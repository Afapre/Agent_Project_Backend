from fastapi import FastAPI
import uvicorn
from src.api.router import general_router
from fastapi.middleware.cors import CORSMiddleware


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
# if __name__=="__main__":
#     uvicorn.run(app='app:app',host='0.0.0.0',port=1234,reload=True)

