# main.py
from fastapi import FastAPI, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from typing import List
import asyncio # Import asyncio for the sleep example

app = FastAPI()

# Add CORS middleware to allow the frontend to access the backend
# Adjust origins in production for better security
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Allows all origins during development
    allow_credentials=True,
    allow_methods=["*"], # Allows all methods (GET, POST, etc.)
    allow_headers=["*"], # Allows all headers
)

@app.get("/")
async def read_root():
    """Basic endpoint to check if the server is running."""
    return {"message": "FastAPI server is running"}

@app.post("/process")
async def process_inputs(
    text: str = Form(None), # text can be optional
    files: List[UploadFile] = File(None) # files can be optional
):
    """
    Receives text and files and simulates starting a process.
    In a real application, this would trigger the actual analysis/generation.
    """
    print("Received request to process:")
    print(f"Text: {text if text is not None else 'No text'}")
    if files:
        print(f"Files received ({len(files)}):")
        for file in files:
            print(f"- {file.filename} ({file.content_type})")
        # You would typically save or process the files here
        # Example: file.read() to get content, file.close() when done
    else:
        print("No files received.")

    # Simulate a short delay before responding - uncomment if desired
    # await asyncio.sleep(1)

    return {
        "status": "success",
        "message": "Input received. Processing simulated on frontend."
    }

# To run the server:
# uvicorn main:app --reload