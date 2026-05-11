import os
import subprocess
from dotenv import load_dotenv
from src.data_logic.doc_processor import process_pdf_to_db
from pyngrok import ngrok
import sys
import time

load_dotenv()

if __name__ == "__main__":
    # 1. Initialize the Knowledge Base
    print("Initializing CLARA's brain...")
    retriever = process_pdf_to_db('Procurement_doc.pdf') 
    
    # 2. Launch UI (Streamlit) FIRST
    print("Launching Interface...")
    venv_python = sys.executable 
    
    # We add PYTHONPATH to the environment so Streamlit finds the 'src' folder
    env = os.environ.copy()
    env["PYTHONPATH"] = os.getcwd()
    
    streamlit_cmd = [venv_python, '-m', 'streamlit', 'run', 'src/interface/app.py']
    streamlit_process = subprocess.Popen(streamlit_cmd, env=env)

    # 3. Wait for Streamlit to open its port
    print("Waiting 20 seconds for CLARA to wake up...")
    time.sleep(20)

    # 4. Setup and Start Ngrok AFTER the app is running
    print("Setting up Ngrok Public Tunnel...")
    ngrok.kill() # Kill any old hanging tunnels
    NGROK_AUTH_TOKEN = os.environ.get('NGROK_AUTH_TOKEN')
    ngrok.set_auth_token(NGROK_AUTH_TOKEN)

    # We use 127.0.0.1 to ensure it hits the local IPv4 address
    public_url = ngrok.connect(8501, bind_tls=True)
    
    print(f'\n🚀 CLARA IS LIVE!')
    print(f'Public URL: {public_url}')
    #print(f'Local URL: http://localhost:8501')
    print("\n✅ All systems running. You can now share the Public URL!")

    # Keep the script running
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Shutting down...")
        ngrok.kill()
        streamlit_process.terminate()