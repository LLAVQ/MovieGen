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
import { ref, Ref, nextTick } from 'vue';
// Import all components
import Header from './components/Header.vue';
import SettingsModal from './components/SettingsModal.vue'; // <-- Ensure this matches your filename
import Gallery from './components/Gallery.vue';
import InputArea from './components/InputArea.vue';
import AnalysisSection from './components/AnalysisSection.vue';
// Import the LogEntry interface from the AnalysisSection component script
import type { LogEntry } from './components/AnalysisSection.vue';

// --- State ---
const settingsModalVisible = ref(false);
const isAnalysisVisible = ref(false);
const textInput = ref('');
const selectedFiles: Ref<FileList | null> = ref(null); // Store FileList from input
const analysisLog: Ref<LogEntry[]> = ref([]);
const progressBarWidth = ref(0);
const isProcessing = ref(false);
let stopGeneration = false; // Flag to signal stopping the simulation

const statueImages: { url: string }[] = [ // Correct type for statueImages
  { url: 'https://upload.wikimedia.org/wikipedia/en/2/2b/The_Motherland_Calls_detail_-_Volgograd%2C_October_2018.jpg' },
  { url: 'https://upload.wikimedia.org/wikipedia/commons/3/31/Berl%C3%ADn%2C_Tiergarten%2C_sov%C4%9Btsk%C3%BD_pam%C3%A1tn%C3%ADk.jpg' },
  { url: 'https://upload.wikimedia.org/wikipedia/commons/4/44/Glory_Mound_-_panoramio.jpg' },
  { url: 'https://upload.wikimedia.org/wikipedia/commons/7/73/Lincoln_and_WWII_memorials.jpg' },
  { url: 'https://upload.wikimedia.org/wikipedia/commons/6/62/Museum_of_the_Great_Patriotic_War_Moscow.jpg' },
  { url: 'https://upload.wikimedia.org/wikipedia/commons/d/df/Victory_Square_%28Ivan_Smelov%29.jpg' },
];

// --- Handlers from InputArea ---
const handleFilesSelected = (files: FileList | null) => {
  selectedFiles.value = files;
};

const handleSend = async ({ text, files }: { text: string; files: FileList | null }) => {
  // Reset state and show analysis section
  stopGeneration = false;
  isProcessing.value = true;
  isAnalysisVisible.value = true;
  analysisLog.value = [];
  progressBarWidth.value = 0;

  // --- Send data to backend ---
  const formData = new FormData();
  if (text) {
    formData.append('text', text);
  }
  if (files) {
    for (let i = 0; i < files.length; i++) {
      formData.append('files', files[i]);
    }
  }

  try {
    const response = await fetch('http://127.0.0.1:8000/process', {
      method: 'POST',
      body: formData,
      // Headers like Content-Type are often set automatically by fetch when using FormData
    });

    if (!response.ok) {
      // If backend response is not OK (e.g., 400, 500 errors)
      const errorData = await response.text(); // Get response body as text
      throw new Error(`HTTP error! status: ${response.status} - ${errorData}`);
    }

    const result = await response.json();
    console.log('Backend response:', result);

    // Backend confirmed receipt, now start frontend simulation of processing
    simulateAnalysis(files ? Array.from(files) : [], text);

  } catch (error: any) { // Use 'any' or a more specific error type if needed
    console.error('Error sending data to backend:', error);
    // Display error message in the log
    addLogEntry('Error', `Processing failed: ${error.message || error}`, true);
    isProcessing.value = false; // Stop processing state
    // Optionally hide analysis section or leave it to show the error
    // isAnalysisVisible.value = false;
  } finally {
      // Clear inputs regardless of success or failure, once processing attempt finishes
      if (!stopGeneration) { // Only clear if stop wasn't manually clicked
          textInput.value = '';
           if (selectedFiles.value) {
                // Clearing the file input requires direct DOM manipulation
                const fileInputEl = document.getElementById('fileUpload') as HTMLInputElement | null;
                if (fileInputEl) {
                    fileInputEl.value = '';
                }
           }
           selectedFiles.value = null;
      }
       // Note: isProcessing is set to false in simulateAnalysis or error block
  }
};

const handleStop = () => {
  stopGeneration = true;
  isProcessing.value = false; // Immediately allow sending again
  isAnalysisVisible.value = false; // Hide analysis section immediately
   // No need to clear inputs here, as they are cleared when processing stops naturally
   // or you could add clearing here too if preferred on manual stop.
};

// --- Simulation Logic (adapted from original JS) ---

const simulateAnalysis = (files: File[], text: string) => {
  if (stopGeneration) return; // Check stop flag early

  let delay = 500; // Initial delay before first entry
  const itemsToProcess = [
      ...files.map(file => ({ type: 'file' as const, data: file })),
      ...(text ? [{ type: 'text' as const, data: text }] : [])
  ];
  let total = itemsToProcess.length;
  let completed = 0;

  const updateProgress = () => {
    if (stopGeneration) return;
    const percent = total > 0 ? Math.round((completed / total) * 100) : 100;
    progressBarWidth.value = percent;
  };

  const processNextItem = (index: number) => {
      if (stopGeneration || index >= itemsToProcess.length) {
          if (!stopGeneration && index === itemsToProcess.length) {
              finish(); // All items processed, now finish
          }
          return; // Stop processing chain
      }

      const item = itemsToProcess[index];

      let itemDelay = 2500; // Delay for each item

      setTimeout(() => {
          if (stopGeneration) return; // Check again after delay
          if (item.type === 'file') {
              analyzeFile(item.data.name);
          } else { // item.type === 'text'
              analyzeText(item.data);
          }

          completed++;
          updateProgress();

          // After processing this item, schedule the next one
          processNextItem(index + 1);

      }, itemDelay);
  };

  const finish = () => {
    if (stopGeneration) return; // Final check
    isProcessing.value = false; // Allow sending again
     // Ensure progress bar reaches 100% if it didn't due to rounding
    progressBarWidth.value = 100;
    addLogEntry('Video Generation', 'Generation complete!', true);
  };

  // Start processing the first item
  processNextItem(0);

   // If there are no items (should be caught by validation, but safety check)
   if (total === 0) {
        finish();
   }
};


const addLogEntry = (title: string, content: string, isComplete = false) => {
   // Create an entry with empty html content initially if not complete
  const newEntry: LogEntry = { title, content, contentHtml: '', isComplete };
  analysisLog.value.push(newEntry);

   // If not complete, start typing animation
   if (!isComplete) {
      // Use the index of the newly added entry
      const entryIndex = analysisLog.value.length - 1;
      // Use nextTick to ensure the element exists in the DOM before typing
      nextTick(() => {
         // Check if the entry still exists at this index before typing
         if (analysisLog.value[entryIndex]) {
              typeText(entryIndex, content, () => {
                 // Typing complete callback
                 if (!stopGeneration && analysisLog.value[entryIndex]) {
                      analysisLog.value[entryIndex].isComplete = true;
                      // Add a checkmark visually in the span content after typing
                      analysisLog.value[entryIndex].contentHtml += ' ✓';
                 }
              });
         }
      });
   } else {
      // If complete from start (e.g., error message), set full content immediately
      newEntry.contentHtml = content;
   }
};

const analyzeFile = (fileName: string) => {
  const content = `Processing file "${fileName}"...`;
  addLogEntry(`File: ${fileName}`, content, false);
};

const analyzeText = (text: string) => {
  // Truncate long text for log display if needed
  const display_text = text.length > 50 ? text.substring(0, 47) + '...' : text;
  const content = `Processing comment: "${display_text}"...`;
  addLogEntry(`Message`, content, false);
};

// Typewriter effect (updates the contentHtml of a specific log entry)
const typeText = (entryIndex: number, text: string, callback: () => void, charIndex = 0) => {
   // Add checks to ensure we don't try to type into an entry that was removed
   if (stopGeneration || entryIndex >= analysisLog.value.length || !analysisLog.value[entryIndex]) {
      return; // Stop if generation is cancelled or entry is invalid
   }

   // Check if the current contentHtml already matches the target content
   // This can prevent issues if updates happen out of order
   if (analysisLog.value[entryIndex].contentHtml === text) {
       callback(); // Already complete
       return;
   }

   if (charIndex < text.length) {
      // Append next character to the contentHtml of the specific entry
      analysisLog.value[entryIndex].contentHtml += text.charAt(charIndex);
      // Use nextTick to ensure DOM update before scheduling next char
      nextTick(() => {
         setTimeout(() => typeText(entryIndex, text, callback, charIndex + 1), 30);
      });
   } else {
      // Typing complete
      callback();
   }
};

</script>

<style>
/* Global styles imported from src/assets/styles.css */
</style>