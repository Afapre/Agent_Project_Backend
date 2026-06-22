<<<<<<< HEAD
# Langchain Agent with RAG

This project implements a Langchain agent with Retrieval-Augmented Generation (RAG) for procurement assistance, featuring a Streamlit web interface.

## Setup

1. **Clone the repository** and navigate to the project directory.

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables:**
   - Copy `.env.example` to `.env`
   - Fill in your API keys:
     - `GOOGLE_API_KEY`: From Google AI Studio
     - `HF_TOKEN`: Hugging Face token
     - `TAVILY_API_KEY`: Tavily API key for web search
     - `NGROK_AUTH_TOKEN`: Ngrok auth token for generating public links

4. **Add your PDF document:**
   - Place your procurement document as `Procurement_doc.pdf` in the root directory.

5. **Run the script:**
   ```bash
   python main.py
   ```

## What the Script Does

- Processes your PDF document using PyMuPDF
- Sets up a vector database with Chroma for semantic search
- Creates an intelligent agent that can:
  - Search your document with RAG
  - Perform web searches using Tavily
  - Negotiate procurement terms using AI reasoning
- Runs a Streamlit web app (`app.py`)
- Starts a local Streamlit server
- Creates a public ngrok tunnel link to share with others

## Sharing with Others

After running the script, you'll get an ngrok URL like `https://xxxx-xx-xxx-xxx-xx.ngrok.io`. Share this link with others and they can access your Streamlit app without needing to run the code themselves!

## Requirements

- Python 3.8+
- All dependencies listed in `requirements.txt`
- Valid API keys for the services mentioned above
=======
# AI-Learning
This repository contains my learnings from the AI course in CAASITECH Academy.
>>>>>>> 97431f2b4caa99c5bced6ba0753f7d56083ac271
