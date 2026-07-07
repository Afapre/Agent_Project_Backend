
from fastapi import FastAPI
import uvicorn
from src.api.router import general_router
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os
load_dotenv()


#Instantiating fastapi class
app=FastAPI(title='CLARA: AI Purchasing Assistant',description='Negotiates prices with suppliers')

# Allow local HTML file setup to query API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


#fxn to check health of the server
@app.get(path='/health')
async def health_check():
    """checks the health of the server"""
    return {'status':'Healthy'}


#adding general router to app
app.include_router(general_router)

#Running the server
if __name__=="__main__":
    # host=os.getenv('HOST', 'localhost')
    # port=int(os.getenv('PORT', '8000'))
    # uvicorn.run(app='app:app', host=host, port=port, reload=True)

    # Render provides the PORT variable; default to 8000 for local testing
    port = int(os.environ.get("PORT", 8000))
    # Must bind to 0.0.0.0 to be accessible from outside the container
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=False)

