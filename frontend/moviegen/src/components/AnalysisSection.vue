<template>
  <div class="analysis-section">
    <div v-if="isProcessing" class="progress-container">
      <div class="progress-bar" :style="{ width: progressBarWidth + '%' }"></div>
    </div>

    <div class="analysis-log" ref="logRef">
      <div v-if="!isProcessing && logEntries.length === 0" class="log-entry initial-message">
           <strong>Status:</strong><br><span>Enter text or attach files above to start the process.</span>
       </div>
       <div v-if="isProcessing && logEntries.length === 0" class="log-entry initial-message">
            <strong>Status:</strong><br><span>Connecting... Waiting for first log entry from backend...</span>
       </div>


      <div v-for="(entry, index) in logEntries" :key="index" class="log-entry">
        <strong>{{ entry.title }}</strong><br>
        <span class="log-content" :class="{ 'check-mark': entry.isComplete }" v-html="entry.contentHtml"></span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, nextTick } from 'vue';
import type { Ref } from 'vue';

// Interface for log entries - must match the structure sent by the backend or created frontend-side
export interface LogEntry {
  title: string;
  content: string; // Original full content (might be used by backend simulation)
  contentHtml: string; // Content displayed in the template (updated by backend via log_update or set directly)
  isComplete: boolean; // Signaled by backend (e.g., via log_update)
}

const props = defineProps<{
  logEntries: LogEntry[]; // Array of log entries from parent (App.vue)
  progressBarWidth: number; // Progress percentage from parent (App.vue)
   isProcessing: boolean; // Added to control progress bar visibility from parent
}>();

const logRef: Ref<HTMLElement | null> = ref(null); // Ref for the log container element

// Watch logEntries array for changes to enable auto-scrolling
// Use deep: true to react to changes within logEntry objects (like contentHtml updates)
watch(() => props.logEntries, () => {
  nextTick(scrollToBottom);
}, { deep: true });


const scrollToBottom = () => {
  if (logRef.value) {
    // Scroll to the bottom of the log container smoothly
    logRef.value.scrollTo({
      top: logRef.value.scrollHeight,
      behavior: 'smooth'
    });
  }
};
</script>

<style scoped>
.analysis-section {
  /* Inherits margin-top from global styles in App.vue */
  background-color: #2a2a2a; /* Background color */
  padding: 20px;
  border-radius: 8px;
  margin-left: 20px; /* Add some horizontal margin */
  margin-right: 20px;
  margin-bottom: 20px; /* Add space below the section */
}

.progress-container {
  width: 100%;
  background-color: #444; /* Background of the progress bar track */
  border-radius: 5px;
  margin-bottom: 15px;
  overflow: hidden; /* Ensure the progress bar fill stays within bounds */
}

.progress-bar {
  height: 10px; /* Height of the progress bar */
  background-color: #007bff; /* Color of the progress bar fill */
  width: 0%; /* Controlled by the progressBarWidth prop */
  transition: width 0.4s ease; /* Smooth animation for the width change */
}

.analysis-log {
  height: 300px; /* Fixed height for the log area */
  overflow-y: auto; /* Add scrollbar when content exceeds height */
  background-color: #333; /* Background color for the log area */
  padding: 15px;
  border-radius: 4px;
  font-size: 0.9rem;
  color: #eee; /* Text color */
  white-space: pre-wrap; /* Preserve line breaks and wrap */
  word-wrap: break-word; /* Break long words */
}

.log-entry {
  margin-bottom: 10px; /* Space between log entries */
  padding-bottom: 5px; /* Padding at the bottom of each entry */
  border-bottom: 1px dashed #555; /* Separator line */
}

.log-entry:last-child {
    border-bottom: none; /* No border for the last entry */
}

.log-entry strong {
  color: #00aaff; /* Title color */
}

/* Style for the initial messages when log is empty */
.log-entry.initial-message {
     text-align: center;
     font-style: italic;
     color: #bbb;
     border-bottom: none; /* No border for initial messages */
     margin-bottom: 0; /* Remove bottom margin */
     padding-bottom: 0; /* Remove bottom padding */
}


/* Style for the log content */
.log-content {
    /* Styles for the text content part */
    /* Backend controls the content via v-html */
}


/* Style for the checkmark (if included in contentHtml) */
.check-mark {
  /* Optional: style for the checkmark or the text when complete */
  /* color: #28a745; Green color */
  font-weight: bold;
}
</style>