# main.py
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from typing import List
import asyncio
import json
import traceback
import random # Corrected import for random number generation

app = FastAPI()

# Add CORS middleware (important for frontend dev server)
# Adjust origins in production for better security
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Allows all origins during development
    allow_credentials=True,
    allow_methods=["*"], # Allows all methods (GET, POST, PUT, DELETE, OPTIONS, PATCH, WEBSOCKET)
    allow_headers=["*"], # Allows all headers
)

@app.get("/")
async def read_root():
    return {"message": "FastAPI server is running"}

# Removed the /process POST endpoint as input will come via WebSocket

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print(f"WebSocket accepted connection from {websocket.client.host}:{websocket.client.port}")

    # State for this specific connection/process
    is_processing = False
    stop_requested = False
    log_entries_count = 0 # Keep track of log entries added in this session for indexing

    try:
        # Keep connection open, wait for messages (like the 'start' message)
        while True:
            # Receive data from frontend. Expecting a JSON message with type 'start' or 'stop'.
            data = await websocket.receive_text()
            message = json.loads(data)
            print(f"Received message: {message}")

            if message.get("type") == "start" and not is_processing:
                is_processing = True
                stop_requested = False # Reset stop flag for a new process
                log_entries_count = 0 # Reset log count for a new process
                text = message.get("text", "")
                file_names: List[str] = message.get("fileNames", []) # Type hint for clarity

                print(f"Starting simulation for Text: '{text}', Files: {file_names}")

                # --- Simulation Logic (now on backend) ---
                # Calculate total steps (files + text + final generation step)
                total_items = len(file_names) + (1 if text else 0) + 1 # Add 1 for final generation step
                completed_items = 0

                async def send_progress():
                    nonlocal completed_items, total_items # Declare nonlocal before use
                    if total_items == 0:
                         percent = 100 # Handle case with no items gracefully
                    else:
                         percent = int((completed_items / total_items) * 100)

                    # Ensure progress doesn't go backwards and caps at 100
                    percent = max(0, min(100, percent))

                    try:
                         await websocket.send_json({"type": "progress", "percent": percent})
                         print(f"Sent progress: {percent}%")
                    except RuntimeError as e:
                         print(f"Error sending progress: {e}")
                         # This might happen if the connection is closed unexpectedly
                         nonlocal stop_requested # Declare nonlocal before use
                         stop_requested = True # Signal outer loop to stop

                async def simulate_typing(log_entry_index: int, full_content: str):
                     nonlocal stop_requested # Declare nonlocal before use
                     # Simulate typewriter effect by sending content updates
                     if stop_requested: return

                     await asyncio.sleep(0.1) # Small delay before typing starts

                     typed_content = ""
                     # Typing speed delay per character
                     typing_delay = 0.03 # seconds per character

                     for char in full_content:
                         if stop_requested: break # Stop typing if requested
                         typed_content += char
                         try:
                             # Send partial content update
                             await websocket.send_json({
                                 "type": "log_update",
                                 "index": log_entry_index,
                                 "contentHtml": typed_content
                             })
                             # Add delay *after* sending the character
                             await asyncio.sleep(typing_delay)
                         except RuntimeError as e:
                             print(f"Error during typing simulation: {e}")
                             stop_requested = True # Signal stop on send error
                             break # Stop the typing loop


                # --- Process Items ---
                # Simulate file processing
                for file_name in file_names:
                    if stop_requested: break # Stop if requested

                    log_title = f"File: {file_name}"
                    log_content = f"Processing file \"{file_name}\"..."

                    # Send initial log entry
                    try:
                        await websocket.send_json({
                            "type": "log",
                            "title": log_title,
                            "content": log_content # Send full content for typing sim
                        })
                    except RuntimeError as e:
                         print(f"Error sending initial file log: {e}")
                         stop_requested = True
                         break # Stop processing files loop

                    if stop_requested: break # Check again after sending log

                    current_log_index = log_entries_count
                    log_entries_count += 1

                    # Simulate typing the content
                    await simulate_typing(current_log_index, log_content)

                    if stop_requested: break # Stop if requested

                    # Simulate file processing time
                    await asyncio.sleep(2 + (random.random() * 1)) # Fake processing delay (2-3 seconds)

                    # Mark file processing as complete
                    completed_items += 1
                    await send_progress()

                    # Send final log update with checkmark
                    if not stop_requested:
                         try:
                             await websocket.send_json({
                                 "type": "log_update",
                                 "index": current_log_index,
                                 "isComplete": True # Signal completion
                             })
                         except RuntimeError as e:
                             print(f"Error sending file log complete: {e}")
                             stop_requested = True
                             break # Stop processing files loop


                # Simulate text processing
                if text and not stop_requested:
                    log_title = "Message"
                     # Correct Python syntax for conditional expression and string length
                    display_text = text[:47] + '...' if len(text) > 50 else text
                    log_content = f"Processing comment: \"{display_text}\"..."

                    # Send initial log entry
                    try:
                        await websocket.send_json({
                            "type": "log",
                            "title": log_title,
                            "content": log_content # Send full content for typing sim
                        })
                    except RuntimeError as e:
                         print(f"Error sending initial text log: {e}")
                         stop_requested = True

                    if not stop_requested:
                         current_log_index = log_entries_count
                         log_entries_count += 1

                         # Simulate typing the content
                         await simulate_typing(current_log_index, log_content)

                         if not stop_requested:
                             # Simulate text processing time
                             await asyncio.sleep(2 + (random.random() * 1)) # Fake processing delay (2-3 seconds)

                             # Mark text processing as complete
                             completed_items += 1
                             await send_progress()

                             # Send final log update with checkmark
                             try:
                                 await websocket.send_json({
                                     "type": "log_update",
                                     "index": current_log_index,
                                     "isComplete": True # Signal completion
                                 })
                             except RuntimeError as e:
                                 print(f"Error sending text log complete: {e}")
                                 stop_requested = True


                # Simulate video generation time (This is the last step)
                if not stop_requested:
                     log_title = "Video Generation"
                     log_content = "Generating video..." # Initial state
                     try:
                         await websocket.send_json({
                            "type": "log",
                            "title": log_title,
                            "content": log_content
                         })
                     except RuntimeError as e:
                         print(f"Error sending initial generation log: {e}")
                         stop_requested = True

                if not stop_requested:
                     current_log_index = log_entries_count
                     log_entries_count += 1

                     # Simulate typing "Generating video..."
                     await simulate_typing(current_log_index, log_content)

                if not stop_requested:
                     await asyncio.sleep(4 + (random.random() * 2)) # Fake generation delay (4-6 seconds)

                     completed_items += 1 # Mark generation step as complete
                     await send_progress() # Send final 100% progress


                # --- Simulation Finished ---
                if not stop_requested:
                    # Update the last log entry to say "complete" if needed,
                    # or just send the final message. Let's send a final status update.
                    final_message_content = "Generation complete!"
                    try:
                         # Ensure the index is valid before updating
                         if log_entries_count > 0:
                             await websocket.send_json({
                                "type": "log_update",
                                "index": log_entries_count - 1, # Update the last entry
                                "contentHtml": final_message_content + ' ✓', # Final text + checkmark
                                "isComplete": True
                             })
                    except RuntimeError as e:
                        print(f"Error sending final generation log: {e}")

                    try:
                        await websocket.send_json({"type": "finish"})
                    except RuntimeError as e:
                         print(f"Error sending finish message: {e}")

                print(f"Simulation {'finished' if not stop_requested else 'stopped'}.")
                is_processing = False # Allow new process


            elif message.get("type") == "stop":
                print("Stop requested by client.")
                stop_requested = True
                # The simulation loops will detect stop_requested and break, eventually
                # reaching the end and setting is_processing to False.
                # No need to explicitly set is_processing = False here.


            else:
                print(f"Ignoring unknown message type from client: {message.get('type')}")

    except WebSocketDisconnect:
        print(f"WebSocket disconnected: {websocket.client.host}:{websocket.client.port}")
        stop_requested = True # Ensure simulation stops if client disconnects
    except json.JSONDecodeError:
         print("Received invalid JSON data on WebSocket.")
         # Optionally send an error message back
         try:
             await websocket.send_json({"type": "error", "message": "Invalid JSON received."})
         except: pass
         stop_requested = True # Stop processing if message format is bad
    except Exception as e:
        print(f"An unexpected error occurred in WebSocket connection: {e}")
        traceback.print_exc() # Print full traceback
        stop_requested = True # Ensure simulation stops on error
        try:
            await websocket.send_json({"type": "error", "message": f"Server error: {str(e)}"})
        except:
             pass # Ignore if sending error message fails

    finally:
        # Clean up resources if necessary
        is_processing = False
        stop_requested = True # Double-ensure stop state
        print(f"WebSocket handler finished for {websocket.client.host}:{websocket.client.port}")
        # Connection is automatically closed when the handler finishes