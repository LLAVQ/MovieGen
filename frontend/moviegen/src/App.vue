<template>
  <Header />

  <div class="settings" @click="settingsModalVisible = !settingsModalVisible">
    <i class="fas fa-cog"></i>
  </div>
  <SettingsModal :is-visible="settingsModalVisible" />

  <Gallery :statues="statueImages" :class="{ hidden: isAnalysisVisible }" />

  <AnalysisSection
    v-if="isAnalysisVisible"
    :log-entries="analysisLog"
    :progress-bar-width="progressBarWidth"
    :is-processing="isProcessing"
    :class="{ hidden: !isAnalysisVisible }"
  />

  <InputArea
    v-model="textInput"
    :is-processing="isProcessing"
    @files-selected="handleFilesSelected"
    @send="handleSend"
    @stop="handleStop"
  />

  </template>

<script setup lang="ts">
import { ref, Ref, nextTick, onUnmounted } from 'vue';
// Import child components
import Header from './components/Header.vue';
import SettingsModal from './components/SettingsModal.vue';
import Gallery from './components/Gallery.vue';
import InputArea from './components/InputArea.vue';
import AnalysisSection from './components/AnalysisSection.vue';
// Import the LogEntry interface from the AnalysisSection component script for type safety
// This interface is needed by App.vue to correctly type analysisLog array
import type { LogEntry } from './components/AnalysisSection.vue';

// --- State ---
const settingsModalVisible = ref(false); // Controls settings modal visibility
const isAnalysisVisible = ref(false); // Controls visibility of the analysis section vs gallery
const textInput = ref(''); // Holds the value of the text input (bound via v-model)
const selectedFiles: Ref<FileList | null> = ref(null); // Holds the FileList from the file input
// Array to store log entries received from backend. Using the LogEntry interface.
// This array is passed as a prop to AnalysisSection.vue
const analysisLog: Ref<LogEntry[]> = ref([]);
const progressBarWidth = ref(0); // Holds the progress bar percentage
const isProcessing = ref(false); // Indicates if a simulation process is ongoing (backend state)

// WebSocket instance state
const websocket: Ref<WebSocket | null> = ref(null);

// Use this to store the message payload if we try to send before the WS is open
let pendingMessage: { type: string; [key: string]: any } | null = null;

// Static data for the gallery images
const statueImages: { url: string }[] = [
  { url: 'https://upload.wikimedia.org/wikipedia/en/2/2b/The_Motherland_Calls_detail_-_Volgograd%2C_October%202018.jpg' },
  { url: 'https://upload.wikimedia.org/wikipedia/commons/3/31/Berl%C3%ADn%2C_Tiergarten%2C_sov%C4%9Btsk%C3%BD_pam%C3%A1tn%C3%ADk.jpg' },
  { url: 'https://upload.wikimedia.org/wikipedia/commons/4/44/Glory_Mound_-_panoramio.jpg' },
  { url: 'https://upload.wikimedia.org/wikipedia/commons/7/73/Lincoln_and_WWII_memorials.jpg' },
  { url: 'https://upload.wikimedia.org/wikipedia/commons/6/62/Museum_of_the_Great_Patriotic_War_Moscow.jpg' },
  { url: 'https://upload.wikimedia.org/wikipedia/commons/d/df/Victory_Square_%28Ivan_Smelov%29.jpg' },
];

// --- WebSocket Connection and Message Handling ---

const connectWebSocket = () => {
    // Prevent creating a new connection if one is already open or connecting
    if (websocket.value && (websocket.value.readyState === WebSocket.OPEN || websocket.value.readyState === WebSocket.CONNECTING)) {
        console.log("WebSocket already connecting or connected. State:", websocket.value.readyState);
        return;
    }

    // Construct the WebSocket URL. Assumes backend is on the same host but port 8000.
    // If backend is on a different host, replace window.location.host.split(':')[0]
    const wsUrl = `ws://${window.location.host.split(':')[0]}:8000/ws`;

    websocket.value = new WebSocket(wsUrl);
    console.log("WebSocket instance created, attempting to connect to", wsUrl); // Log connection attempt

    // --- WebSocket Event Handlers ---
    websocket.value.onopen = () => {
        console.log("WebSocket connected. Ready state:", websocket.value?.readyState); // Log successful connection
        // If a message was queued while connecting, send it now
        if (pendingMessage) {
             console.log("WS connected. Sending pending message:", pendingMessage);
             sendWebSocketMessage(pendingMessage); // Use helper to send the stored message
             pendingMessage = null; // Clear the pending message after sending
        } else {
             console.log("WS connected. No pending message to send.");
        }
    };

    websocket.value.onmessage = (event) => {
        try {
            // Messages from the backend are expected to be JSON strings
            const message = JSON.parse(event.data);
            console.log("--- Received message from backend:", message); // Log every message received

            switch (message.type) {
                case 'log':
                    console.log("Processing 'log' message.");
                    // Add a new log entry to the analysisLog array
                    // Backend provides index (id), title, full content (for its sim), and initial isComplete (false)
                     const newEntry: LogEntry = {
                         // Use the index provided by the backend as the id/index for our frontend array
                         // This relies on backend sending them in order (0, 1, 2...)
                         // A more robust way would be if backend sent a unique ID, but index is simpler for this simulation
                         title: message.title,
                         content: message.content, // Store original content if needed, though not displayed directly
                         contentHtml: '', // Start with empty HTML content; backend will send updates via log_update
                         isComplete: false
                     };
                     // Push the new entry. The index in analysisLog.value array will match backend's index for this simulation.
                    analysisLog.value.push(newEntry);

                    // Scrolling is handled by the watcher in AnalysisSection.vue based on analysisLog changes
                    break;
                case 'log_update':
                    console.log("Processing 'log_update' message for index", message.index);
                    // Update an existing log entry in the analysisLog array using the index provided by backend
                    if (message.index !== undefined && analysisLog.value[message.index]) {
                        // Update the contentHtml (used for typing effect)
                        if (message.contentHtml !== undefined) {
                            analysisLog.value[message.index].contentHtml = message.contentHtml;
                        }
                        // Update the completion status
                        if (message.isComplete !== undefined) {
                             analysisLog.value[message.index].isComplete = message.isComplete;
                             // If marked complete by backend, ensure checkmark is added visually
                              if (message.isComplete) {
                                   // Check if it doesn't already have one to avoid duplicates on re-update
                                   if (!analysisLog.value[message.index].contentHtml.endsWith(' ✓')) {
                                        analysisLog.value[message.index].contentHtml += ' ✓';
                                   }
                              }
                        }
                         // Scrolling is handled by the watcher in AnalysisSection.vue based on analysisLog changes
                    } else {
                         console.warn("Received log_update for invalid index:", message.index, "Current log length:", analysisLog.value.length);
                         // This can happen if a log_update arrives before the corresponding 'log' message, or indices are off.
                         // For this simulation, indices should be sequential.
                    }
                    // Scrolling is handled by the watcher in AnalysisSection.vue based on log content changes
                    break;
                case 'progress':
                    console.log("Processing 'progress' message:", message.percent);
                    // Update the progress bar percentage
                    progressBarWidth.value = message.percent;
                     // Ensure progress bar visually reaches 100% at the very end
                     if (message.percent >= 100) {
                          nextTick(() => progressBarWidth.value = 100);
                     }
                    break;
                case 'finish':
                    console.log("Simulation finished as signaled by backend.");
                    // The simulation is complete, allow sending a new request
                    isProcessing.value = false;
                    // Ensure progress is 100% on finish
                    progressBarWidth.value = 100;
                    // Final log entry update (like "Generation complete!") is handled by backend sending a final log_update
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
                // Add handlers for other message types if the backend sends them
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

    websocket.value.onerror = (event) => {
        // Handle WebSocket connection errors
        console.error("WebSocket error observed:", event);
        isProcessing.value = false; // Allow sending again on error
        addFrontendErrorLogEntry("WebSocket error. Check backend server console."); // Log error in the log area
         pendingMessage = null; // Clear pending message on connection error
    };

    websocket.value.onclose = (event) => {
        // Handle WebSocket connection closing
        console.log("WebSocket connection closed:", event.code, event.reason);
         // Check if processing was expected to be ongoing when the connection closed
         if (isProcessing.value) {
             console.warn("WebSocket closed unexpectedly during processing.");
             addFrontendErrorLogEntry("Connection closed during processing.");
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

// Handles files selected in the InputArea file input
const handleFilesSelected = (files: FileList | null) => {
  selectedFiles.value = files; // Update state with the selected file list
};

// Handles the 'send' event from the InputArea (user clicks send button)
const handleSend = ({ text, files }: { text: string; files: FileList | null }) => {
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

  // --- Prepare Message for Backend ---
  // Collect file names to send to the backend. Backend only needs names for this simulation.
  const fileNames = files ? Array.from(files).map(f => f.name) : [];

  // Create the message payload to send to the backend to start the simulation
  const startMessage = {
      type: 'start', // Message type recognized by backend
      text: text, // Text input content
      fileNames: fileNames // List of selected file names
  };

  console.log("handleSend triggered. Start message payload:", startMessage); // Log the payload being prepared

  // --- WebSocket Connection Check and Send ---
  // Check the current state of the WebSocket connection:
  if (!websocket.value || websocket.value.readyState === WebSocket.CLOSED) {
      // If not initialized or closed, create a new instance and connect.
      // Store the message to send once the connection is open.
      console.log("WS not initialized or closed. Connecting and storing message:", startMessage);
      pendingMessage = startMessage; // Store the message object
      connectWebSocket(); // Initiate connection
  } else if (websocket.value.readyState === WebSocket.CONNECTING) {
       // If the connection is already in progress, just store the message.
       // It will be sent automatically by the onopen handler when the connection is ready.
       console.log("WS connecting. Storing message:", startMessage);
       pendingMessage = startMessage; // Store the message object
  }
   else if (websocket.value.readyState === WebSocket.OPEN) {
      // If the connection is already open, send the message immediately.
      console.log("WS is already open. Sending message directly.");
      sendWebSocketMessage(startMessage); // Use helper function to send the message
       // No pendingMessage needed as it's sent now
  } else {
       // Handle any other unexpected states (e.g., WebSocket.CLOSING)
       console.error("Unexpected WebSocket state when trying to send:", websocket.value.readyState);
       isProcessing.value = false; // Assume failure to start
       isAnalysisVisible.value = false; // Hide analysis if send fails
       addFrontendErrorLogEntry("Failed to start process: Unexpected WebSocket state.");
  }

  // --- Clear Inputs ---
  // Clear the inputs immediately after the user clicks send.
  textInput.value = ''; // Clear the text input value
   const fileInputEl = document.getElementById('fileUpload') as HTMLInputElement | null;
   if (fileInputEl) {
       fileInputEl.value = ''; // Clear the visual file input (resets selected files)
   }
  selectedFiles.value = null; // Clear the stored file list state

};

// Handles the 'stop' event from the InputArea (user clicks stop button)
const handleStop = () => {
  console.log("handleStop triggered.");
  // If the WebSocket is open, send a stop message to the backend
  if (websocket.value && websocket.value.readyState === WebSocket.OPEN) {
    console.log("Sending stop message via WebSocket.");
    try {
        websocket.value.send(JSON.stringify({ type: 'stop' })); // Send the stop command
    } catch (e) {
         console.error("Error sending stop message:", e);
    }
    // We don't immediately close the WS connection here.
    // We let the backend receive the 'stop' command and potentially
    // finish its current micro-step or clean up, and the connection
    // might be closed by the backend or stay open for future requests.
    // Frontend state updates are handled below for responsiveness.
  } else {
      // If WS isn't open, nothing is processing on the backend for this connection.
      // Just update frontend state as if it stopped.
      console.warn("Stop requested but WebSocket is not open.");
  }

  // --- Update Frontend State ---
  // Update frontend state immediately on stop click for responsiveness
   isProcessing.value = false; // Allow sending a new request
   isAnalysisVisible.value = false; // Hide the analysis section and show the gallery

    // If there was a pending message (user clicked send, then stop before WS opened), clear it.
    if (pendingMessage) {
        console.log("Stop triggered while a message was pending. Clearing pending message.");
        pendingMessage = null;
    }
};


// --- Helper for adding frontend-side error logs ---
// This is used for errors detected on the frontend (WS connection error, message parsing error)
const addFrontendErrorLogEntry = (message: string) => {
     analysisLog.value.push({
         // For frontend errors, we don't have a backend index, create a unique enough ID
         // Using negative index based on current length to avoid collision with backend indices (0, 1, 2...)
         title: 'Error', // Title for error logs
         content: message, // Store original content
         contentHtml: `Error: ${message}`, // Display full message immediately
         isComplete: true // Mark error logs as complete immediately
     });
      // Ensure the log scrolls to the bottom after adding the error
      // Use nextTick to wait for the DOM update
      nextTick(() => {
           const logEl = document.querySelector('.analysis-log');
           if (logEl) {
               logEl.scrollTop = logEl.scrollHeight;
           }
      });
}

// --- Lifecycle Hook ---
// Ensure WebSocket is closed when the component instance is unmounted
// This is good practice if App.vue might be destroyed (e.g., routing in a larger app)
onUnmounted(() => {
    console.log("App component unmounted. Closing WebSocket.");
    closeWebSocket();
});

// Note: We are connecting the WebSocket only when the 'Send' button is clicked for the first time
// or if a pending message is waiting. If you preferred to keep a connection open
// throughout the app's lifecycle, you could call connectWebSocket in onMounted.

</script>

<style>
/* Global styles imported from src/assets/styles.css */
/* Component-specific styles are scoped within each component file */
</style>