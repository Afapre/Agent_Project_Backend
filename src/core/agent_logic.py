from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import create_agent


with open('src/utils/system_prompt.md', 'r') as f:
    SYSTEM_PROMPT = f.read()

def get_clara_agent(tools, api_key):
    model = ChatGoogleGenerativeAI(api_key=api_key, model='gemini-3.1-flash-lite-preview',
     temperature=0.2 # Lower temperature prevents analytical looping
    )
    return create_agent(model=model, system_prompt=SYSTEM_PROMPT, tools=tools)


# import datetime
# from google.genai import types
# from google.genai import client
# from langchain_google_genai import ChatGoogleGenerativeAI
# from langchain.agents import create_agent

# with open('src/utils/system_prompt.md', 'r') as f:
#     SYSTEM_PROMPT = f.read()

# def get_clara_agent(tools, api_key):
#     # Initialize the core client to handle the context cache layer
#     ai_client = client.Client(api_key=api_key)
#     model_name = 'gemini-3.1-flash-lite-preview'
#     cache_name = 'clara_prompt_cache'
    
#     try:
#         # Check if the prompt cache already exists on Google's servers
#         loaded_cache = ai_client.caches.get(name=cache_name)
#     except Exception:
#         # Create a fresh cache if it does not exist
#         # We explicitly inject your system prompt into the cached contents
#         loaded_cache = ai_client.caches.create(
#             model=model_name,
#             config=types.CreateCachedContentConfig(
#                 contents=[SYSTEM_PROMPT],
#                 id=cache_name,
#                 # Cache will persist for 1 hour of inactivity before regenerating
#                 ttl=datetime.timedelta(hours=1), 
#             )
#         )

#     # Instantiate the LangChain model wrapper linking to your cached content
#     model = ChatGoogleGenerativeAI(
#         api_key=api_key, 
#         model=model_name,
#         temperature=0.2,
#         # Pass the unique cache reference directly to the model configuration
#         extra_body={"cached_content": loaded_cache.name}
#     )
    
#     return create_agent(model=model, system_prompt=SYSTEM_PROMPT, tools=tools)

