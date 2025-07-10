from backend.app.db.base import init_db
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os

app = FastAPI()

# This is important for allowing the frontend (running on a different port)
# to communicate with the backend.
origins = [
    "http://localhost:3000", # The Nuxt frontend
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup_event():
    print("Starting up the FastAPI application...")
    init_db()

@app.get("/")
def read_root():
    return {"status": "Backend is running!"}

@app.get("/api/test")
def test_api():
    # Example of reading an environment variable
    mal_id = os.getenv("MAL_CLIENT_ID", "Not Set")
    return {
        "message": "Hello from FastAPI!",
        "mal_client_id_is_set": mal_id != "Not Set"
    }