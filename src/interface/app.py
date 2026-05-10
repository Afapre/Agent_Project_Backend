import streamlit as st
import os
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, AIMessage
from src.data_logic.doc_processor import process_pdf_to_db
from src.tools.tools_definition import get_tools
from src.core.agent_logic import get_clara_agent

# Load environment variables
load_dotenv()
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
TAVILY_API_KEY = os.getenv('TAVILY_API_KEY')

# --- UI CONFIGURATION (Matching your original) ---
st.set_page_config(page_title="CLARA AI Purchasing Assistant", page_icon="🤖", layout="wide")
st.title("CLARA: AI Purchasing Assistant")
st.write("🙋‍♀️Hi I'm CLARA, let's talk about procurement and pricing!")

# --- INITIALIZATION ---
@st.cache_resource
def initialize_system():
    try:
        retriever = process_pdf_to_db('Procurement_doc.pdf')
        tools = get_tools(retriever, TAVILY_API_KEY)
        agent = get_clara_agent(tools, GOOGLE_API_KEY)
        return agent
    except Exception as e:
        st.error(f"Error cleaning PDF: {e}. Please ensure 'Procurement_doc.pdf' is accessible.")
        st.stop()

agent = initialize_system()

# --- CHAT HISTORY ---
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display existing messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# --- USER INTERACTION ---
if prompt := st.chat_input("Enter your message to CLARA..."):
    # Add user message to state
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Generate Assistant Response
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""
        
        # Convert session history to LangChain message format
        history = []
        for msg in st.session_state.messages:
            if msg["role"] == "user":
                history.append(HumanMessage(content=msg["content"]))
            else:
                history.append(AIMessage(content=msg["content"]))

        # Stream the response
        try:
            for chunk in agent.stream({'messages': history}, stream_mode='messages'):
                # We need to check if the chunk is a message and get its content
                if isinstance(chunk, tuple):
                    msg = chunk[0]
                else:
                    msg = chunk
                
                if hasattr(msg, 'content'):
                    # Ensure content is a string
                    content = msg.content
                    if isinstance(content, list):
                        # If it's a list (common in some versions), join it into a string
                        text = "".join([c['text'] if isinstance(c, dict) else str(c) for c in content])
                    else:
                        text = str(content)
                        
                    full_response += text
                    message_placeholder.markdown(full_response + "▌")
            
            message_placeholder.markdown(full_response)
            st.session_state.messages.append({"role": "assistant", "content": full_response})
        except Exception as e:
            st.error(f"An error occurred while generating the response: {e}")