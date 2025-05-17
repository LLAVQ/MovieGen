import os
import json
import base64
import uuid
import asyncio
import websockets.exceptions # Import specific WebSocket exception types

from fastapi import FastAPI, WebSocket, HTTPException
from fastapi.responses import HTMLResponse # Optional: for a basic root endpoint
from pydantic import BaseModel # For message validation

# --- File Analysis Libraries ---
# Import necessary libraries for file analysis.
# We use try-except blocks to allow the server to start even if some are missing,
# but functionality for those file types will be skipped.
try:
    # python-docx for .docx files. Note: Does NOT support older .doc format.
    from docx import Document
except ImportError:
    print("python-docx not found. .docx file analysis will be skipped.")
    Document = None # Set to None if the import fails

try:
    # pdfminer.six for .pdf files.
    # Alternative: pymuPDF (fitz) is often faster and more robust for PDFs. Install with 'pip install pymupdf'
    from pdfminer.high_level import extract_text as extract_text_from_pdf
except ImportError:
    print("pdfminer.six not found. .pdf file analysis will be skipped.")
    extract_text_from_pdf = None # Set to None if the import fails

# --- AI Model Library (g4f) ---
# Import the g4f client.
try:
    from g4f.client import Client
    # Initialize the g4f client instance. This will be used to interact with AI models.
    gpt_client = Client()
except ImportError:
    print("g4f not found. AI analysis will be skipped.")
    gpt_client = None # Set to None if the import fails
    # Define dummy objects to prevent errors if g4f is not installed.
    # This provides a fallback response message.
    class DummyGPTResponse:
        def __init__(self, content="AI analysis skipped: g4f library not installed or available."):
            # Structure matches the expected response from g4f client's create method
            self.choices = [DummyMessage(content=content)]
    class DummyMessage:
        def __init__(self, content):
            # Structure matches the expected message object within choices
            self.message = DummyContent(content=content)
    class DummyContent:
         def __init__(self, content):
              # Structure matches the expected content attribute of the message
              self.content = content


# --- FastAPI App Initialization ---
app = FastAPI()

# --- Configuration ---
# Directory where uploaded files will be saved, organized by task ID.
UPLOAD_DIR = "uploaded_tasks"
# Create the upload directory if it doesn't already exist.
os.makedirs(UPLOAD_DIR, exist_ok=True)


# --- Pydantic Model for WebSocket Messages ---
# Defines the expected structure of JSON messages received from the frontend.
class WebSocketMessage(BaseModel):
    type: str # Indicates the type of message (e.g., "start", "stop")
    text: str = None # Optional text input from the user
    file_names: list[str] = [] # List of original names of attached files
    file_data: list[str] = [] # List of base64 encoded contents of the attached files
    settings: dict = {} # Optional dictionary for settings or parameters


# --- File Text Extraction Function ---
# Asynchronous function to extract text from a given file path.
async def extract_text_from_file(file_path: str):
    """
    Extracts text from supported file types (.docx, .pdf, .txt, .md, .csv).
    Runs potentially blocking I/O and CPU tasks in a thread pool.
    """
    file_name = os.path.basename(file_path) # Get just the file name from the path
    _, file_extension = os.path.splitext(file_name) # Split into name and extension
    file_extension = file_extension.lower() # Convert extension to lowercase

    text = "" # Initialize extracted text
    skipped = False # Flag if extraction was skipped (e.g., unsupported type or missing lib)
    error = None # Store any error message during extraction

    try:
        if file_extension == ".docx":
            if Document: # Check if python-docx was imported successfully
                document = Document(file_path)
                text = "\n".join([paragraph.text for paragraph in document.paragraphs])
            else:
                text = f"(.docx analysis skipped: python-docx not installed)"
                skipped = True
        elif file_extension == ".pdf":
            if extract_text_from_pdf: # Check if pdfminer.six was imported successfully
                # Run PDF extraction in a separate thread to avoid blocking the event loop,
                # as it can be CPU-bound.
                text = await asyncio.to_thread(extract_text_from_pdf, file_path)
            else:
                text = f"(.pdf analysis skipped: pdfminer.six not installed)"
                skipped = True
        elif file_extension in [".txt", ".md", ".csv"]: # Handle common plain text types
             # Run file reading in a separate thread to avoid blocking the event loop.
             text = await asyncio.to_thread(lambda: open(file_path, 'r', encoding='utf-8', errors='ignore').read())
        else:
            # If the file extension is not recognized, skip analysis for this file.
            text = f"(Analysis skipped: Unsupported file type '{file_extension}')"
            skipped = True

    except Exception as e:
        # Catch any errors that occur during file processing (e.g., file corruption, decoding issues)
        error = f"Error extracting text: {e}"
        text = f"(Error extracting text from {file_name}: {e})"
        print(f"Error extracting text from {file_name}: {e}") # Log the error on the backend console

    # Return a dictionary containing the extracted text, skipped status, and error message.
    return {
        "text": text,
        "skipped": skipped,
        "error": error
    }

# --- Typing Simulation Placeholder ---
# This function is designed to simulate a character-by-character typing effect
# on the frontend by sending incremental updates ('log_update' messages).
# If you don't need this effect, you can simplify this function or remove its calls.
async def simulate_typing(websocket: WebSocket, index: int, content: str):
    """
    Simulates character-by-character typing effect for a log entry.
    Sends 'log_update' messages to the frontend.
    (Implement your actual typing logic here if needed, or keep this placeholder)
    """
    # If content is empty, send an empty update and mark as complete.
    if not content:
        await websocket.send_json({"type": "log_update", "index": index, "contentHtml": "", "isComplete": True})
        return

    # Simple simulation: send the whole content at once after a small delay.
    # Replace this with a loop that sends characters incrementally if a typing effect is desired.
    await asyncio.sleep(0.1) # Small delay before sending content
    # Send the full content as HTML (replacing newlines with <br> for display).
    await websocket.send_json({"type": "log_update", "index": index, "contentHtml": content.replace('\n', '<br>'), "isComplete": True})


# --- WebSocket Endpoint Definition ---
# This is the main endpoint for WebSocket communication.
@app.websocket("/ws")
async def handle_websocket(websocket: WebSocket):
    # Accept the incoming WebSocket connection.
    await websocket.accept()
    print("WebSocket accepted connection.")

    # Counter to track the index of log entries for the frontend's typing simulation.
    log_entries_count = 0

    try:
        # Keep the connection open in a loop to receive multiple messages from the frontend.
        while True:
            # Receive a message from the frontend.
            message_data = await websocket.receive_text()
            print(f"Received message: {message_data}") # Log the raw received message

            try:
                # Parse the received JSON string and validate it against the WebSocketMessage model.
                message = json.loads(message_data)
                msg = WebSocketMessage(**message) # Pydantic validation happens here

            except Exception as e:
                # If parsing or validation fails, send an error message back to the frontend and continue the loop.
                print(f"Error parsing or validating message: {e}")
                await websocket.send_json({"type": "error", "message": f"Invalid message format: {e}"})
                continue # Continue waiting for the next message

            # --- Process Messages Based on Type ---
            if msg.type == "start":
                # --- Handle the Start Message to Initiate Processing ---
                print("Received start message. Initiating task.")

                # Generate a unique task ID to create a dedicated directory for this task's files.
                task_id = str(uuid.uuid4())
                task_dir = os.path.join(UPLOAD_DIR, task_id)
                # Create the task-specific directory.
                os.makedirs(task_dir, exist_ok=True)

                # Send initial log messages to the frontend about task start and ID.
                await websocket.send_json({"type": "log", "title": "Task Started", "content": f"Assigned task ID: {task_id}"})
                # Use simulate_typing for the log title
                await simulate_typing(websocket, log_entries_count, "Task Started")
                current_log_index_title = log_entries_count # Store the index for the title log
                log_entries_count += 1
                # Send the content as a separate log entry and simulate typing its content
                await websocket.send_json({"type": "log", "title": "", "content": f"Assigned task ID: {task_id}"})
                await simulate_typing(websocket, log_entries_count, f"Assigned task ID: {task_id}")
                log_entries_count += 1


                # Variables to accumulate extracted text and store individual file results.
                all_extracted_text = ""
                extracted_file_results = []

                # --- 1. Process Uploaded Files ---
                if msg.file_names and msg.file_data and len(msg.file_names) == len(msg.file_data):
                    await websocket.send_json({"type": "log", "title": "Processing Files", "content": f"Received {len(msg.file_names)} file(s)."})
                    await simulate_typing(websocket, log_entries_count, "Processing Files")
                    current_log_index_title = log_entries_count
                    log_entries_count += 1
                    await websocket.send_json({"type": "log", "title": "", "content": f"Received {len(msg.file_names)} file(s)."})
                    await simulate_typing(websocket, log_entries_count, f"Received {len(msg.file_names)} file(s).")
                    log_entries_count += 1


                    for i, file_name in enumerate(msg.file_names):
                        # Send log messages indicating processing for each file.
                        await websocket.send_json({"type": "log", "title": f"Processing File: {file_name}", "content": f"Saving and extracting text from {file_name}..."})
                        await simulate_typing(websocket, log_entries_count, f"Processing File: {file_name}")
                        current_log_index_title = log_entries_count
                        log_entries_count += 1
                        await websocket.send_json({"type": "log", "title": "", "content": f"Saving and extracting text from {file_name}..."})
                        await simulate_typing(websocket, log_entries_count, f"Saving and extracting text from {file_name}...")
                        log_entries_count += 1


                        file_path = os.path.join(task_dir, file_name)
                        extracted_text_content = ""
                        extraction_status = "Pending" # Initial status

                        try:
                            # Decode the base64 file data to bytes.
                            file_content_base64 = msg.file_data[i]
                            file_content_bytes = base64.b64decode(file_content_base64)

                            # Ensure the task directory exists (redundant with os.makedirs above, but safe).
                            os.makedirs(task_dir, exist_ok=True)
                            # Save the binary file content to the task-specific directory.
                            # Run file writing in a separate thread.
                            await asyncio.to_thread(lambda: open(file_path, "wb").write(file_content_bytes))
                            print(f"Saved file: {file_path}") # Log save confirmation on backend

                            # Send a log message confirming the file was saved.
                            await websocket.send_json({"type": "log", "title": f"Saved: {file_name}", "content": f"File saved to {file_path}"})
                            await simulate_typing(websocket, log_entries_count, f"Saved: {file_name}")
                            log_entries_count += 1
                            await websocket.send_json({"type": "log", "title": "", "content": f"File saved to {file_path}"})
                            await simulate_typing(websocket, log_entries_count, f"File saved to {file_path}")
                            log_entries_count += 1


                            # Extract text from the saved file using the helper function.
                            extract_result = await extract_text_from_file(file_path)
                            extracted_text_content = extract_result["text"]
                            extraction_skipped = extract_result["skipped"]
                            extraction_error = extract_result["error"]

                            # Determine the final extraction status.
                            if extraction_error:
                                extraction_status = f"Error: {extraction_error}"
                            elif extraction_skipped:
                                extraction_status = "Skipped"
                            else:
                                extraction_status = "Success"

                            # Accumulate text for the main GPT prompt only if extraction was successful and not skipped.
                            if not extraction_skipped and not extraction_error:
                                all_extracted_text += f"\n\n--- Text from {file_name} ---\n{extracted_text_content}"

                            # Store the result for this specific file to send back to the frontend.
                            extracted_file_results.append({
                                "file_name": file_name,
                                "text": extracted_text_content,
                                "status": extraction_status
                            })

                            # Send a log message indicating the extraction status for this file.
                            await websocket.send_json({"type": "log", "title": f"Extraction Status: {file_name}", "content": f"Status: {extraction_status}"})
                            await simulate_typing(websocket, log_entries_count, f"Extraction Status: {file_name}")
                            log_entries_count += 1
                            await websocket.send_json({"type": "log", "title": "", "content": f"Status: {extraction_status}"})
                            await simulate_typing(websocket, log_entries_count, f"Status: {extraction_status}")
                            log_entries_count += 1


                        except Exception as e:
                            # Catch errors specific to processing this file (e.g., base64 decode failure).
                            print(f"Error processing file {file_name} after base64 decode: {e}")
                            extraction_status = f"Processing Error: {e}"
                            extracted_file_results.append({
                                "file_name": file_name,
                                "text": f"Could not process file: {e}", # Provide an error message as text content
                                "status": extraction_status
                            })
                            await websocket.send_json({"type": "log", "title": f"File Processing Error: {file_name}", "content": f"Could not process {file_name}: {e}"})
                            await simulate_typing(websocket, log_entries_count, f"File Processing Error: {file_name}")
                            log_entries_count += 1
                            await websocket.send_json({"type": "log", "title": "", "content": f"Could not process {file_name}: {e}"})
                            await simulate_typing(websocket, log_entries_count, f"Could not process {file_name}: {e}")
                            log_entries_count += 1


                    # Send all extracted file texts as a batch with the 'extracted_texts' message type.
                    # The frontend will display these results in the AnalysisSection.
                    if extracted_file_results:
                         await websocket.send_json({"type": "extracted_texts", "results": extracted_file_results})


                # --- 2. Prepare Prompt for AI Model ---
                # Combine the user's text input and the accumulated extracted text for the AI prompt.
                prompt_parts = []
                if msg.text and msg.text.strip():
                    prompt_parts.append(msg.text.strip())
                    await websocket.send_json({"type": "log", "title": "User Input Text Included", "content": f"Including user text: {msg.text.strip()[:100]}..."})
                    await simulate_typing(websocket, log_entries_count, "User Input Text Included")
                    log_entries_count += 1
                    await websocket.send_json({"type": "log", "title": "", "content": f"Including user text: {msg.text.strip()[:100]}..."})
                    await simulate_typing(websocket, log_entries_count, f"Including user text: {msg.text.strip()[:100]}...")
                    log_entries_count += 1


                if all_extracted_text.strip():
                    # Add a header before the extracted text for clarity in the prompt.
                    prompt_parts.append("--- Extracted Text from Files ---\n" + all_extracted_text.strip())
                    await websocket.send_json({"type": "log", "title": "File Text Included in Prompt", "content": "Including extracted text from files in the AI prompt."})
                    await simulate_typing(websocket, log_entries_count, "File Text Included in Prompt")
                    log_entries_count += 1
                    await websocket.send_json({"type": "log", "title": "", "content": "Including extracted text from files in the AI prompt."})
                    await simulate_typing(websocket, log_entries_count, "Including extracted text from files in the AI prompt.")
                    log_entries_count += 1


                final_prompt_content = "\n\n".join(prompt_parts)

                # If there is no content (user text or extracted text), skip the AI call.
                if not final_prompt_content.strip():
                     await websocket.send_json({"type": "log", "title": "No Content for AI", "content": "No user text or file text provided for AI analysis."})
                     await simulate_typing(websocket, log_entries_count, "No Content for AI")
                     log_entries_count += 1
                     await websocket.send_json({"type": "log", "title": "", "content": "Skipping AI call."})
                     await simulate_typing(websocket, log_entries_count, "Skipping AI call.")
                     log_entries_count += 1

                     await websocket.send_json({"type": "finish"}) # Signal task completion
                     print("Sent finish message (no content for AI).")
                     continue # Skip the rest of the loop iteration


                # --- 3. Call AI Model using g4f (Requesting YAML Output with Speaker Text) ---
                # Define the system message instructing the AI to provide YAML output.
                # This message guides the AI on its role and the desired output format.
                system_message = """
You are an AI assistant tasked with generating structured YAML output for text-to-video models.
Analyze the user's input and extracted text. Based on the content, create a sequence of 'frames' or 'scenes'.
Each frame/scene should represent a detailed and themed visual or textual element for a video sequence.
Instead of a fixed duration, provide the text that a speaker should say during that frame/scene.
Output the result strictly in valid YAML format.

Here is the requested YAML structure. Ensure your output adheres to this format:

frames:
  - frame_id: 1 # Unique identifier for the frame (starting from 1)
    speaker_text: "Welcome to our presentation on the history of this monument." # The text the speaker should say for this frame
    text_content: "The Monument's History" # Text to display on screen in this frame (if any)
    scene_description: "An establishing shot of the monument on a sunny day." # A brief description of the visual scene or image for this frame
    # Add other relevant optional fields if applicable:
    # transition: "fade-in" # Optional transition effect (fade, slide, etc.)
    # timing_offset: 0.5 # Optional offset within the speaker_text duration for when text/scene appears

  - frame_id: 2
    speaker_text: "Built in 1945, it commemorates a significant event."
    text_content: "Established 1945"
    scene_description: "Archival footage of the monument's construction."

  # ... more frames as needed

Ensure the entire response is valid YAML and is NOT enclosed in any code block delimiters like ``` or '''.
If no relevant content is provided after analysis, return an empty frames list or a message in YAML format indicating no content.
Be concise and relevant to the input text when creating frames.
"""

                # The content from the user and files becomes the user message content for the AI.
                user_message_content = f"Input for YAML framing:\n\n{final_prompt_content}"

                # Send log messages indicating the AI call is starting.
                await websocket.send_json({"type": "log", "title": "Calling AI Model", "content": "Sending combined text to AI model for YAML framing."})
                await simulate_typing(websocket, log_entries_count, "Calling AI Model")
                log_entries_count += 1
                await websocket.send_json({"type": "log", "title": "", "content": "Waiting for YAML response..."})
                await simulate_typing(websocket, log_entries_count, "Waiting for YAML response...")
                log_entries_count += 1

                # Default response content in case of error or if g4f is not available.
                gpt_response_content = "AI analysis skipped: g4f library not installed or error."

                # Check if the gpt_client was successfully initialized.
                if gpt_client:
                    try:
                        # Call the g4f model to generate the response.
                        # We use asyncio.to_thread because the g4f client call might be blocking.
                        response = await asyncio.to_thread(
                            gpt_client.chat.completions.create,
                            model="gpt-4o-mini", # Use the specified model
                            # Provide the messages list including the system and user messages.
                            messages=[
                                {"role": "system", "content": system_message},
                                {"role": "user", "content": user_message_content}
                            ],
                            web_search=False # As per the user's requirement
                        )
                        # Extract the content from the AI's response.
                        gpt_response_content = response.choices[0].message.content

                        # Send log messages indicating the response was received.
                        await websocket.send_json({"type": "log", "title": "AI Response Received", "content": "YAML response received from AI model."})
                        await simulate_typing(websocket, log_entries_count, "AI Response Received")
                        log_entries_count += 1
                        await websocket.send_json({"type": "log", "title": "", "content": "Sending YAML response to frontend."})
                        await simulate_typing(websocket, log_entries_count, "Sending YAML response to frontend.")
                        log_entries_count += 1

                        # Send the final GPT response (the YAML string) back to the frontend.
                        # The frontend will display this in the AnalysisSection.
                        await websocket.send_json({"type": "gpt_response", "content": gpt_response_content})

                    except Exception as e:
                        # Catch any errors that occur during the g4f API call.
                        print(f"Error calling g4f: {e}")
                        gpt_response_content = f"Error calling AI model: {e}"
                        # Send log messages indicating the AI call error.
                        await websocket.send_json({"type": "log", "title": "AI Error", "content": gpt_response_content})
                        await simulate_typing(websocket, log_entries_count, "AI Error")
                        log_entries_count += 1
                        await websocket.send_json({"type": "log", "title": "", "content": gpt_response_content})
                        await simulate_typing(websocket, log_entries_count, gpt_response_content)
                        log_entries_count += 1

                else:
                    # If g4f client was not initialized (e.g., library not installed), send a skipped message.
                     await websocket.send_json({"type": "log", "title": "AI Skipped", "content": gpt_response_content})
                     await simulate_typing(websocket, log_entries_count, "AI Skipped")
                     log_entries_count += 1
                     await websocket.send_json({"type": "log", "title": "", "content": gpt_response_content})
                     await simulate_typing(websocket, log_entries_count, gpt_response_content)
                     log_entries_count += 1


                # --- 4. Signal Task Completion ---
                # Send a 'finish' message to the frontend to indicate the task is complete.
                await websocket.send_json({"type": "finish"})
                print("Sent finish message.")

            # --- Handle the Stop Message ---
            elif msg.type == "stop":
                print("Received stop message. Implementing stop logic (placeholder).")
                # In a real application, you would add logic here to stop any ongoing processing.
                # For this example, we just acknowledge the stop request and send a finish message.
                await websocket.send_json({"type": "log", "title": "Task Stopped", "content": "Processing stopped as requested."})
                await simulate_typing(websocket, log_entries_count, "Task Stopped")
                log_entries_count += 1
                await websocket.send_json({"type": "log", "title": "", "content": "Processing halted."})
                await simulate_typing(websocket, log_entries_count, "Processing halted.")
                log_entries_count += 1

                await websocket.send_json({"type": "finish"}) # Signal task completion after stopping
                print("Sent finish message after stop.")

            # --- Handle Unknown Message Types ---
            else:
                print(f"Received unknown message type: {msg.type}")
                await websocket.send_json({"type": "error", "message": f"Unknown message type: {msg.type}"})


    # --- WebSocket Exception Handling ---
    # Handle cases where the WebSocket connection is closed by the client normally.
    except websockets.exceptions.ConnectionClosedOK:
        print("WebSocket connection closed normally.")
    # Handle cases where the WebSocket connection is closed with an error.
    except websockets.exceptions.ConnectionClosedError as e:
        print(f"WebSocket connection closed with error: {e}")
        # You might decide to log this error or handle it differently.
        # Sending an error message back might not be possible if the connection is already completely broken.
    # Handle any other unexpected exceptions that occur within the WebSocket handler.
    except Exception as e:
        print(f"An unexpected error occurred in the WebSocket handler: {e}")
        # Attempt to send a general error message back to the frontend before the connection closes.
        try:
             await websocket.send_json({"type": "error", "message": f"An internal server error occurred: {e}"})
        except Exception:
             # If sending the error message fails (e.g., connection is already completely broken), just ignore.
             pass
    # --- Finally Block ---
    finally:
        # Code in this block will run when the WebSocket connection is closed for any reason.
        print("WebSocket handler finally block executed.")
        # Resource cleanup (like closing files) could be added here if needed,
        # but temporary task directories are kept for now based on the UPLOAD_DIR logic.


# --- Optional: Basic Root Endpoint ---
# This is a standard HTTP GET endpoint, not part of the WebSocket communication.
# It's useful for checking if the FastAPI server is running.
@app.get("/")
async def read_root():
    # Returns a simple HTML response.
    return HTMLResponse("""
        <!DOCTYPE html>
        <html>
        <head>
            <title>FastAPI Backend</title>
        </head>
        <body>
            <h1>FastAPI Backend is running!</h1>
            <p>WebSocket endpoint is at <code>/ws</code></p>
            <p>Make sure to run the frontend application to interact via WebSocket.</p>
        </body>
        </html>
    """)

# To run this file:
# Save it as main.py
# Run the command: uvicorn main:app --reload
