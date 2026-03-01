# ============================================================
# Token Server - FastAPI
# Generates Stream tokens for frontend clients
# ============================================================

# FastAPI framework for creating REST API
from fastapi import FastAPI

# CORS middleware to allow React frontend to call this API
from fastapi.middleware.cors import CORSMiddleware

# Stream server SDK for generating tokens
from getstream import Stream

# Load environment variables from .env file
from dotenv import load_dotenv
import os

# Load .env keys
load_dotenv()

# Read Stream credentials from .env
STREAM_API_KEY = os.getenv("STREAM_API_KEY")
STREAM_API_SECRET = os.getenv("STREAM_API_SECRET")

print(STREAM_API_SECRET )

# Create FastAPI app instance
app = FastAPI()

# ============================================================
# CORS SETUP
# Allow React frontend (localhost:5173) to call this server
# ============================================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite default port
    allow_credentials=True,
    allow_methods=["*"],   # Allow all HTTP methods
    allow_headers=["*"],   # Allow all headers
)

# Create Stream server client using API credentials

stream_client = Stream(
    api_key=STREAM_API_KEY,
    api_secret=STREAM_API_SECRET,
    timeout=10,
)

# ============================================================
# TOKEN ENDPOINT
# React frontend calls this to get a valid Stream token
# ============================================================
@app.get("/token/{user_id}")
def get_token(user_id: str):
    """
    Generate a Stream token for the given user ID.
    Frontend calls: GET /token/candidate_abc123
    Returns: { "token": "xxxxx", "api_key": "yyyyy" }
    """

    # Generate token for this user using Stream server SDK
    token = stream_client.create_token(user_id)

    # Return token and API key to frontend
    return {
        "token": token,           # JWT token for Stream authentication
        "api_key": STREAM_API_KEY # API key frontend needs for StreamVideoClient
    }

# ============================================================
# HEALTH CHECK ENDPOINT
# To verify server is running
# ============================================================
@app.get("/health")
def health():
    return {"status": "ok", "message": "Token server is running"}

# ============================================================
# RUN SERVER
# ============================================================
if __name__ == "__main__":
    import uvicorn
    # Start server on port 8000
    uvicorn.run(app, host="0.0.0.0", port=8000)