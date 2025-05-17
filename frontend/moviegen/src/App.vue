<script setup lang="ts">
import { ref, Ref, nextTick, onUnmounted, onMounted } from 'vue';
// Import child components
import Header from './components/Header.vue';
import SettingsModal from './components/SettingsModal.vue';
import Gallery from './components/Gallery.vue';
import InputArea from './components/InputArea.vue';
import AnalysisSection from './components/AnalysisSection.vue';
// Import the LogEntry interface from the AnalysisSection component script for type safety
import type { LogEntry } from './components/AnalysisSection.vue';

// --- State ---
const settingsModalVisible = ref(false); // Controls settings modal visibility
const isAnalysisVisible = ref(false); // Controls visibility of the analysis section vs gallery
// textInput and selectedFiles are managed internally by InputArea now,
// and their values are passed via the @send event payload.

// Array to store log entries received from backend or created frontend-side.
const analysisLog: Ref<LogEntry[]> = ref([]);
const progressBarWidth = ref(0); // Holds the progress bar percentage
const isProcessing = ref(false); // Indicates if a process (backend task) is ongoing

// State for storing analysis results (extracted text and GPT response)
const extractedFileTexts = ref<{ file_name: string; text: string; status: string }[]>([]); // List of results per file
const gptResponse = ref<string | null>(null); // The final response from the AI model

// State for general error messages
const errorStatus = ref<string | null>(null);

// WebSocket instance state
const websocket: Ref<WebSocket | null> = ref(null);

// Use this to store the message payload if we try to send before the WS is open
// It will be sent automatically by the onopen handler.
let pendingMessage: { type: string; [key: string]: any } | null = null;

// Static data for the gallery images
const statueImages: { url: string }[] = [
  { url: 'https://upload.wikimedia.org/wikipedia/en/2/2b/The_Motherland_Calls_detail_-_Volgograd%2C_October%202018.jpg' },
  { url: 'https://upload.wikimedia.org/wikipedia/commons/3/31/Berl%C3%ADn%2C_Tiergarten%2C_sov%C4%9Btsk%C3%bd_pam%C4%9btn%C3%ADk.jpg' },
  { url: 'https://upload.wikimedia.org/wikipedia/commons/4/44/Glory_Mound_-_panoramio.jpg' },
  { url: 'https://upload.wikimedia.org/wikipedia/commons/7/73/Lincoln_and_WWII_memorials.jpg' },
  { url: 'https://upload.wikimedia.org/wikipedia/commons/6/62/Museum_of_the_Great_Patriotic_War_Moscow.jpg' },
  { url: 'https://upload.wikimedia.org/wikipedia/commons/d/df/Victory_Square_%28Ivan_Smelov%29.jpg' },
];

// --- WebSocket Connection and Message Handling ---

// Connects the WebSocket. Called on mount or when sending if not connected.
const connectWebSocket = () => {
    // Prevent creating a new connection if one is already open or connecting
    if (websocket.value && (websocket.value.readyState === WebSocket.OPEN || websocket.value.readyState === WebSocket.CONNECTING)) {
        console.log("WebSocket already connecting or connected. State:", websocket.value?.readyState);
        return; // Exit if connection is already in desired states
    }

    // Construct the WebSocket URL. Assumes backend is on the same host but port 8000.
    // Use VITE_WEBSOCKET_URL from .env if available, otherwise construct from window location.
    const wsUrl = import.meta.env.VITE_WEBSOCKET_URL || `ws://${window.location.host.split(':')[0]}:8000/ws`;

    websocket.value = new WebSocket(wsUrl); // Create a new WebSocket instance
    console.log("WebSocket instance created, attempting to connect to", wsUrl); // Log connection attempt

    // --- WebSocket Event Handlers ---
    websocket.value.onopen = () => {
        console.log("WebSocket connected. Ready state:", websocket.value?.readyState); // Log successful connection
        errorStatus.value = null; // Clear any previous connection errors

        // If a message was queued while connecting, send it now
        if (pendingMessage) {
             console.log("WS connected. Sending pending message:", pendingMessage);
             sendWebSocketMessage(pendingMessage); // Use helper to send the stored message
             pendingMessage = null; // Clear the pending message after sending
        } else {
             console.log("WS connected. No pending message to send.");
        }
    };

    // Handles messages received from the backend
    websocket.value.onmessage = (event) => {
        try {
            // Messages from the backend are expected to be JSON strings
            const message = JSON.parse(event.data);
            console.log("--- Received message from backend:", message); // Log every message received

            // Process the message based on its 'type' field
            switch (message.type) {
                case 'log':
                    console.log("Processing 'log' message.");
                    // Add a new log entry to the analysisLog array
                     const newEntry: LogEntry = {
                         title: message.title || 'Status Update', // Use a default title if none provided
                         content: message.content || '', // Store original content
                         contentHtml: message.content || '', // Initially display full content in log
                         isComplete: false // Mark as not complete initially (backend will send update)
                     };
                    // Add new entry to the log. The index in analysisLog.value array will correspond to backend's index
                    analysisLog.value.push(newEntry);
                    // Scrolling is handled by the watcher in AnalysisSection.vue

                    // If the log entry is the first one related to processing, show the analysis section
                    if (analysisLog.value.length === 1 && message.type === 'log' && message.title !== 'Task Started') {
                         isAnalysisVisible.value = true; // Show analysis section
                    } else if (analysisLog.value.length === 0 && message.type === 'log' && message.title === 'Task Started') {
                         // Special case for the very first log entry 'Task Started'
                         isAnalysisVisible.value = true; // Show analysis section
                    }

                    break;
                case 'log_update':
                    console.log("Processing 'log_update' message for index", message.index);
                    // Update an existing log entry in the analysisLog array using the index provided by backend
                    // This is typically used for typing simulation or updating status of a specific step
                    if (message.index !== undefined && analysisLog.value[message.index]) {
                        // Update the contentHtml (used for typing effect or final content)
                        if (message.contentHtml !== undefined) {
                            analysisLog.value[message.index].contentHtml = message.contentHtml;
                        }
                        // Update the completion status (e.g., to show a checkmark)
                        if (message.isComplete !== undefined) {
                             analysisLog.value[message.index].isComplete = message.isComplete;
                             // Optionally add a visual indicator like a checkmark if complete
                              if (message.isComplete) {
                                   // Ensure checkmark is added only once per entry
                                   if (!analysisLog.value[message.index].contentHtml.endsWith(' ✓')) {
                                        analysisLog.value[message.index].contentHtml += ' ✓';
                                   }
                              }
                        }
                         // Scrolling is handled by the watcher in AnalysisSection.vue based on log content changes
                    } else {
                         console.warn("Received log_update for invalid index:", message.index, "Current log length:", analysisLog.value.length);
                         // This might indicate messages are out of order.
                    }
                    break;
                case 'progress':
                    console.log("Processing 'progress' message:", message.percentage);
                    // Update the progress bar percentage
                    progressBarWidth.value = message.percentage;
                     // Ensure progress bar visually reaches 100% at the very end
                     if (message.percentage >= 100) {
                          nextTick(() => progressBarWidth.value = 100);
                     }
                    break;
                case 'file_texts': // New message type: results of file text extraction
                     console.log("Processing 'file_texts' message.");
                     // Store the extracted text results for display in the results section
                     if (message.results && Array.isArray(message.results)) {
                         extractedFileTexts.value = message.results;
                     } else {
                         console.warn("Received 'file_texts' message with unexpected results format:", message.results);
                     }
                     // You might want to add a general log entry indicating file analysis is complete
                      analysisLog.value.push({
                          title: "File Analysis Results",
                         content: `Processed ${extractedFileTexts.value.length} file(s) for text extraction.`,
                         contentHtml: `Processed ${extractedFileTexts.value.length} file(s) for text extraction.`,
                          isComplete: true // Mark as complete
                     });
                    break;
                case 'gpt_response': // New message type: the final AI model response
                     console.log("Processing 'gpt_response' message.");
                     // Store the GPT response content for display in the results section
                     gptResponse.value = message.content || 'No response content.';
                     // You might want to add a log entry indicating the response is received
                      analysisLog.value.push({
                          title: "AI Model Response Received",
                         content: "AI model analysis complete. See results below.",
                         contentHtml: "AI model analysis complete. See results below.",
                          isComplete: true
                     });
                    break;
                case 'finish':
                    console.log("Task finished as signaled by backend.");
                    // The backend task is complete, allow sending a new request
                    isProcessing.value = false;
                    progressBarWidth.value = 100; // Ensure progress is 100% on finish
                    // A final log entry update (like "Generation complete!") might be sent by backend before 'finish'
                    pendingMessage = null; // Ensure no pending message after finish
                    break;
                 case 'error':
                    // Backend reported an error during processing
                    console.error("Backend reported error:", message.message);
                     // Display the error message in the log area
                     addFrontendErrorLogEntry(`Backend Error: ${message.message}`); // Use helper to add a log entry for the error
                     isProcessing.value = false; // Allow sending again
                     pendingMessage = null; // Clear pending message on error
                     // Optionally, close the WebSocket connection or show a specific error state
                    break;
                default:
                    console.warn("Received message with unknown type:", message.type, message);
            }
        } catch (e) {
            // Handle errors if the received data is not valid JSON or processing the message fails
            console.error("Failed to parse or process WebSocket message:", e, "Received data:", event.data);
             addFrontendErrorLogEntry(`Frontend Error processing message: ${e}`); // Log error in the log area
             isProcessing.value = false; // Allow sending again
             // Clear any pending message as processing failed
             pendingMessage = null;
             // Optionally try to close the WS if message parsing/processing fails consistently
        }
    };

    // Event handler for WebSocket connection errors
    websocket.value.onerror = (event) => {
        // Handle WebSocket connection errors
        console.error("WebSocket error observed:", event);
        isProcessing.value = false; // Allow sending again on error
        errorStatus.value = "WebSocket connection error. Check backend server console."; // Display connection error status
        addFrontendErrorLogEntry("WebSocket connection error."); // Log error in the log area
         pendingMessage = null; // Clear pending message on connection error
    };

    // Event handler for WebSocket connection closing
    websocket.value.onclose = (event) => {
        console.log("WebSocket connection closed:", event.code, event.reason);
         // Check if processing was expected to be ongoing when the connection closed
         if (isProcessing.value) {
             console.warn("WebSocket closed unexpectedly during processing.");
             // Add a log entry for unexpected closure during processing
             addFrontendErrorLogEntry("Connection closed unexpectedly during processing.");
         } else if (pendingMessage) {
              console.warn("WebSocket closed before sending pending message.");
               addFrontendErrorLogEntry("Connection closed before starting process (WS error).");
         } else if (event.code === 1000) {
             console.log("WebSocket closed cleanly (Code 1000)."); // Code 1000 is normal closure
         } else {
              console.log(`WebSocket closed unexpectedly. Code: ${event.code}, Reason: ${event.reason}`);
               addFrontendErrorLogEntry(`WebSocket closed unexpectedly (Code: ${event.code}).`);
         }

        isProcessing.value = false; // Allow sending again
        websocket.value = null; // Clear the WebSocket instance reference
        pendingMessage = null; // Clear pending message on close
    };
};

// Helper function to send a message over the WebSocket
const sendWebSocketMessage = (message: { type: string; [key: string]: any }) => {
    // Check if WS is open before trying to send
    if (websocket.value && websocket.value.readyState === WebSocket.OPEN) {
        console.log("Attempting to send WS message:", message); // Log right before sending
        websocket.value.send(JSON.stringify(message)); // Send the message as a JSON string
        console.log("WS message sent successfully (client-side call)."); // Log after send() call
    } else {
        // This case indicates an issue with the WS state when trying to send.
        // It should ideally be prevented by the connection check in handleSend.
        console.error("WebSocket not available or not open to send message. Ready state:", websocket.value?.readyState);
         isProcessing.value = false; // Assume failure
         isAnalysisVisible.value = false; // Hide analysis if send fails
         addFrontendErrorLogEntry("Failed to send message: WebSocket not ready.");
         pendingMessage = null; // Clear pending message if somehow got here with one
    }
};

// Helper function to close the WebSocket connection cleanly
const closeWebSocket = () => {
    // Only try to close if a websocket instance exists and is not already closing or closed
    if (websocket.value && (websocket.value.readyState === WebSocket.OPEN || websocket.value.readyState === WebSocket.CONNECTING)) {
        console.log("Closing WebSocket connection...");
        // Optionally send a stop message to the backend before closing if a process might be running
        if (isProcessing.value) {
             try {
                 websocket.value.send(JSON.stringify({ type: 'stop' }));
                 console.log("Sent stop message before closing WS.");
             } catch (e) {
                  console.error("Error sending stop message during close:", e);
             }
        }
        // Close the connection. Use code 1000 for normal closure.
        // Reason can be a short string (max 123 bytes).
        websocket.value.close(1000, 'Client closing');
    } else if (websocket.value && websocket.value.readyState === WebSocket.CONNECTING) {
        console.log("WebSocket connecting, abandoning connection attempt.");
        // No explicit close needed, just let onerror/onclose handle it
         websocket.value = null; // Clear reference
         pendingMessage = null;
         isProcessing.value = false;
         // isAnalysisVisible.value = false; // Decide if you hide analysis on abandoned connect
         addFrontendErrorLogEntry("Connection attempt abandoned.");
    } else {
        console.log("WebSocket is not open or connecting, nothing to close.");
    }
     // Ensure frontend state is reset regardless of close success
     isProcessing.value = false;
     pendingMessage = null; // Clear pending message
     websocket.value = null; // Clear the reference
};


// --- Handlers triggered by InputArea component events ---

// Handles the 'send' event from the InputArea (user clicks send button or presses Enter)
// Receives text and files from the InputArea component
const handleSend = async ({ text, files }: { text: string; files: File[] }) => {
    // Basic validation: require text or files
    if (!text.trim() && (!files || files.length === 0)) {
     alert("Введите текст или выберите файл");
     return; // Stop if no input
    }

    // --- Prepare Frontend State for New Process ---
    // Update frontend state immediately on Send click for responsiveness
    isProcessing.value = true; // Indicate that a process is starting (client side)
    isAnalysisVisible.value = true; // Show the analysis section (hides gallery)
    analysisLog.value = []; // Clear any previous log entries
    progressBarWidth.value = 0; // Reset the progress bar
    extractedFileTexts.value = []; // Clear previous extracted texts
    gptResponse.value = null; // Clear previous GPT response
    errorStatus.value = null; // Clear previous general errors


    // Prepare file data for sending (read as base64)
    // Use Promise.all to handle multiple files asynchronously
    const fileDataPromises = files.map(file => {
        return new Promise<string>((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = () => {
                // Read file content as ArrayBuffer
                const arrayBuffer = reader.result as ArrayBuffer;
                const bytes = new Uint8Array(arrayBuffer);
                let binaryString = '';
                // Convert byte array to a binary string
                bytes.forEach(byte => {
                    binaryString += String.fromCharCode(byte);
                });
                // Encode the binary string to base64
                const base64String = btoa(binaryString);
                resolve(base64String); // Resolve the promise with the base64 string
            };
             reader.onerror = reject; // Reject the promise if file reading fails
             reader.readAsArrayBuffer(file); // Read file content as ArrayBuffer
        });
    });

    try {
        // Wait for all files to be read and converted to base64
        const fileBase64Data = await Promise.all(fileDataPromises);

        // Extract just the file names
         const fileNames = files.map(file => file.name);

        // Construct the message payload for the backend
         const message = {
             type: 'start', // Message type recognized by backend
             text: text, // User input text
             file_names: fileNames, // Names of the attached files
             file_data: fileBase64Data, // Base64 encoded content of the files
             settings: {} // Placeholder for settings if you implement them
         };

        console.log("handleSend triggered. Attempting to send WS message:", message); // Log the payload being prepared

        // --- WebSocket Connection Check and Send ---
        // Check the current state of the WebSocket connection:
        if (!websocket.value || websocket.value.readyState === WebSocket.CLOSED) {
            // If not initialized or closed, create a new instance and connect.
            // Store the message to send once the connection is open.
            console.log("WS not initialized or closed. Connecting and storing message:", message);
            pendingMessage = message; // Store the message object
            connectWebSocket(); // Initiate connection
        } else if (websocket.value.readyState === WebSocket.CONNECTING) {
             // If the connection is already in progress, just store the message.
             // It will be sent automatically by the onopen handler when the connection is ready.
             console.log("WS connecting. Storing message:", message);
             pendingMessage = message; // Store the message object
        }
         else if (websocket.value.readyState === WebSocket.OPEN) {
            // If the connection is already open, send the message immediately.
            console.log("WS is already open. Sending message directly.");
            sendWebSocketMessage(message); // Use helper function to send the message
             // No pendingMessage needed as it's sent now
        } else {
             // Handle any other unexpected states (e.g., WebSocket.CLOSING)
             console.error("Unexpected WebSocket state when trying to send:", websocket.value.readyState);
             isProcessing.value = false; // Assume failure to start
             isAnalysisVisible.value = false; // Hide analysis if send fails
             addFrontendErrorLogEntry("Failed to start process: Unexpected WebSocket state.");
        }

        // --- Clear Inputs ---
        // Clearing inputs is handled by InputArea internally after emitting 'send'

    } catch (error) {
        // Handle errors that occur during file reading before sending
        console.error("Error reading files:", error);
        isProcessing.value = false; // Stop processing state
        errorStatus.value = `Error reading files: ${error.message}`;
         // Add a log entry for the file reading error
         addFrontendErrorLogEntry(`Error reading files before sending: ${error.message}`);
    }
};

// Handle the 'stop' event (if InputArea emits it, though previous version didn't)
// This function would be called if there's a "Stop" button in InputArea
const handleStop = () => {
  console.log("handleStop triggered.");
  // If the WebSocket is open and processing is active, send a stop message to the backend
  if (websocket.value && websocket.value.readyState === WebSocket.OPEN && isProcessing.value) {
    console.log("Sending stop message via WebSocket.");
    try {
        websocket.value.send(JSON.stringify({ type: 'stop' })); // Send the stop command
    } catch (e) {
         console.error("Error sending stop message:", e);
         addFrontendErrorLogEntry(`Error sending stop message: ${e}`);
    }
    // Frontend state updates will happen when the backend confirms stop or connection closes
  } else {
      // If WS isn't open or not processing, nothing is processing on the backend for this connection.
      console.warn("Stop requested but WebSocket is not open or not processing.");
      // Just update frontend state as if it stopped immediately
       isProcessing.value = false; // Allow sending a new request
       isAnalysisVisible.value = false; // Hide the analysis section and show the gallery
       if (pendingMessage) { // If there was a pending message, clear it
           console.log("Clearing pending message on stop request.");
           pendingMessage = null;
       }
  }
};


// --- Helper for adding frontend-side error logs ---
// This is used for errors detected on the frontend (WS connection error, message parsing error)
const addFrontendErrorLogEntry = (message: string) => {
     // Create a log entry for the error. Use a distinct title.
     const errorLogEntry: LogEntry = {
         title: 'Frontend Error', // Title for frontend error logs
         content: message, // Store original content
         contentHtml: `<span style="color: red;">Error: ${message}</span>`, // Display error message in red
         isComplete: true // Mark error logs as complete immediately
     };
      analysisLog.value.push(errorLogEntry); // Add the error log entry

      // Ensure the log scrolls to the bottom after adding the error
      // Use nextTick to wait for the DOM update before attempting to scroll
      nextTick(() => {
           const logEl = document.querySelector('.analysis-log');
           if (logEl) {
               // Check if scrollHeight is greater than clientHeight before scrolling
               if (logEl.scrollHeight > logEl.clientHeight) {
                    logEl.scrollTop = logEl.scrollHeight;
               }
           }
      });
}


// --- Lifecycle Hook ---
// Connect WebSocket when the component is mounted to the DOM.
// Consider if you want to connect immediately on mount or only when the first message is sent.
// The current logic connects on first send or if pending message exists.
// If you want a persistent connection, call connectWebSocket() here:
// onMounted(() => {
//   console.log("App mounted. Connecting WebSocket.");
//   connectWebSocket();
// });


// Ensure WebSocket is closed when the component instance is unmounted
// This is good practice if App.vue might be destroyed (e.g., routing in a larger app)
onUnmounted(() => {
    console.log("App component unmounted. Closing WebSocket.");
    closeWebSocket();
});

// Note: The WebSocket connection is initiated in handleSend if it's not already open.
// This means the WS connection is created when the user first interacts by sending a message.


</script>

<template>
  <div>
    <Header />

    <button class="settings-button" @click="settingsModalVisible = !settingsModalVisible">
        <i class="fas fa-cog"></i> </button>

    <SettingsModal :is-visible="settingsModalVisible" @close="settingsModalVisible = false" @save="handleSettingsUpdate" />

    <Gallery v-if="!isAnalysisVisible" :statues="statueImages" />

    <AnalysisSection
      v-if="isAnalysisVisible"
      :log-entries="analysisLog"
      :progress-bar-width="progressBarWidth"
      :is-processing="isProcessing"
      />

    <InputArea
      :is-processing="isProcessing"
      @send="handleSend"
      />
      <div v-if="errorStatus" class="error-status">{{ errorStatus }}</div>


     <div class="results-section" v-if="extractedFileTexts.length > 0 || gptResponse !== null">
        <h3>Analysis Results:</h3>
         <div v-for="(fileResult, index) in extractedFileTexts" :key="index" class="file-result">
             <h4>Text from {{ fileResult.file_name }} (Status: {{ fileResult.status }}):</h4>
              <pre>{{ fileResult.text }}</pre>
         </div>
         <div v-if="gptResponse !== null" class="gpt-response">
             <h4>AI Model Response:</h4>
             <pre>{{ gptResponse }}</pre>
         </div>
     </div>


  </div>
</template>


<style>
/* Global styles for the application */
body {
    margin: 0;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif;
    background-color: #1e1e1e; /* Dark background */
    color: white; /* Default text color */
    padding-bottom: 100px; /* Add padding at the bottom to prevent input area from covering content */
    /* Add padding top if needed to avoid header overlap if AnalysisSection isn't always first content */
}

/* Global header positioning (details like height/width/colors are in Header.vue scoped styles) */
header {
    position: fixed; /* Fix header position */
    top: 20px;       /* Distance from the top */
    left: 30px;      /* Distance from the left */
    z-index: 1000;   /* Ensure header is above other content */
    /* Other Header styles are in Header.vue */
}

 /* Remove old .logo styles from here if they exist in your global CSS file */
 /* They should be handled by Header.vue now */
 /*
.logo { ... }
.logo::after { ... }
.logo:hover::after { ... }
*/


/* Keep other global styles if you have them (e.g., for Gallery) */
.gallery-container { /* ... */ }
.statue { /* ... */ }

/* Style for the Gallery when it's hidden (using v-if now, but keep hidden class definition if used elsewhere) */
/* If using v-if on Gallery and AnalysisSection, you might not need the .hidden class here for them */
/*
.hidden {
    display: none;
}
*/


/* Adjust margin for analysis section and results section to not be hidden by fixed header */
/* analysis-section has margin-top: 180px in its scoped styles */
/* Add margin-top to .results-section if it can appear above analysis logs */
/* If AnalysisSection is ALWAYS shown before results, margin-top on results-section will be relative to analysis-section end */


/* Style for the error status message */
.error-status {
    color: red; /* Red text for errors */
    text-align: center;
    margin-top: 20px;
    padding: 10px;
    background-color: #330000; /* Dark red background */
    border-radius: 4px;
    margin-left: 20px;
    margin-right: 20px;
}

/* Style for the settings button */
.settings-button {
    position: fixed; /* Fixed position */
    top: 20px;       /* Distance from the top */
    right: 30px;     /* Distance from the right */
    z-index: 1000;   /* Ensure button is above other content */
    background: none; /* No background fill */
    border: none; /* No border */
    font-size: 1.5rem; /* Icon size */
    cursor: pointer; /* Indicate it's clickable */
    color: white; /* Icon color */
     transition: transform 0.3s ease; /* Smooth transition on hover/active */
     padding: 0; /* Remove default button padding */
     width: 40px; /* Give it a fixed size for easier clicking */
     height: 40px;
     display: flex; /* Use flexbox to center icon */
     justify-content: center;
     align-items: center;
}
.settings-button:hover {
    transform: rotate(90deg); /* Rotate icon on hover */
}


/* Styles for displaying analysis results (extracted text and GPT response) */
/* This section now appears after AnalysisSection in the template */
.results-section {
    margin-top: 20px; /* Space above this section */
    padding: 20px;
    background-color: #2a2a2a; /* Slightly lighter dark background for this section */
    border-radius: 8px;
    margin-left: 20px; /* Add some horizontal margin */
    margin-right: 20px;
    margin-bottom: 100px; /* Add margin at the bottom to prevent input area overlap */
}

.results-section h3 {
     color: #007bff; /* Blue color for the main heading */
     border-bottom: 1px solid #007bff; /* Underline the main heading */
     padding-bottom: 10px;
     margin-bottom: 20px;
}

.results-section h4 {
    color: #00aaff; /* Lighter blue for subheadings (file names, AI response) */
    margin-top: 15px;
    margin-bottom: 10px;
}

/* Style for the preformatted text display */
.results-section pre {
    background-color: #333; /* Darker background for the code/text block */
    padding: 15px;
    border-radius: 4px;
    overflow-x: auto; /* Add horizontal scroll if text is too wide */
    white-space: pre-wrap; /* Preserve line breaks and wrap long lines */
    word-wrap: break-word; /* Break words if necessary */
    color: #eee; /* Light grey text color */
    font-size: 0.9rem;
}

.file-result, .gpt-response {
    margin-bottom: 20px; /* Space between file results and GPT response */
}

.gpt-response pre {
    /* Specific styles for the GPT response pre block if needed */
    /* font-style: italic; */
}


</style>