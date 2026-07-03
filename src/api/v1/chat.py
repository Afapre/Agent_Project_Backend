import os
import re 
from dotenv import load_dotenv
from typing import List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from langchain_core.messages import HumanMessage, AIMessage
from src.core.agent_logic import get_clara_agent
from src.tools.tools_definition import get_tools
from src.data_logic.doc_processor import PDFProcessor
from src.schema.chat_models import ChatRequest,ChatResponse
from src.exceptions.harmful_exceptions import HarmfulContentError
from src.addons.text_to_speech import text_to_speech
load_dotenv()


router = APIRouter()

@router.post(path='/message', response_model=ChatResponse)
async def chat_with_clara(payload: ChatRequest):
    """
    Submits a message prompt along with conversational history to CLARA 
    and returns a cleaned, parsed text response.
    """

    # Gather secret keys from your environment
    google_key = os.getenv('GOOGLE_API_KEY')
    tavily_key = os.getenv('TAVILY_API_KEY')
        
    if not google_key:
        raise HTTPException(status_code=500, detail="Missing GOOGLE_API_KEY environment variable.")  
    
    try:
        processor = PDFProcessor()
        #retriever = processor.retrieve_from_db()
        collection=processor.collection
        tools = get_tools(collection, tavily_key)
        agent = get_clara_agent(tools, google_key)

        # Skip the prompt-guard model entirely for lighter startup and lower memory use.
        user_prompt = payload.prompt.strip()

        # --- FIX: UNCOMMENT & FEED CHAT HISTORY TO LANGCHAIN ---
        # Convert past conversational payloads into LangChain structures
        formatted_history = []
        
        # Check if history exists in payload before looping(Runs only if input is verified as safe)
        if hasattr(payload, 'history') and payload.history:
            for msg in payload.history:
                if msg.get('role') == "user" or msg.get('role') == "human":
                    formatted_history.append(HumanMessage(content=msg.get('content')))
                elif msg.get('role') == "assistant" or msg.get('role') == "ai":
                    formatted_history.append(AIMessage(content=msg.get('content')))
       
        # Append the incoming prompt as the final user message
        formatted_history.append(HumanMessage(content=user_prompt))

        # Invoke the agent execution layer using the FULL message chain sequence
        # If your agent uses standard message states, pass 'messages': formatted_history
        response = agent.invoke({'messages': formatted_history})
        
        # --- (Keep your existing structural text parsing code below) ---
        if isinstance(response, dict) and 'messages' in response:
            message_list = response['messages']
            ai_msg = None
            for msg in reversed(message_list):
                if hasattr(msg, 'type') and msg.type == 'ai':
                    ai_msg = msg
                    break
                elif hasattr(msg, '__class__') and msg.__class__.__name__ == 'AIMessage':
                    ai_msg = msg
                    break
            raw_content = ai_msg.content if ai_msg else message_list[-1].content
        else:
            raw_content = response.content if hasattr(response, 'content') else response
     

        final_text = ""
        if isinstance(raw_content, list):
            for item in raw_content:
                if isinstance(item, dict) and 'text' in item:
                    final_text += item['text']
                elif isinstance(item, str):
                    final_text += item
        else:
            final_text = str(raw_content).strip()
        
        audio_base64=text_to_speech(final_text)
        return ChatResponse(response=final_text.strip(),audio=audio_base64 if audio_base64 else None)
    
    except HarmfulContentError as e:
        raise HTTPException(status_code=403, detail=f"Harmful Content Execution Failure: {str(e)}")
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail=f"Agent Execution Failure: {str(e)}")
