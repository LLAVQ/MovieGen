<template>
  <div class="analysis-section">
    <div class="progress-container">
      <div class="progress-bar" :style="{ width: progressBarWidth + '%' }"></div>
    </div>

    <div class="analysis-log" ref="logRef">
      <div v-for="(entry, index) in logEntries" :key="index" class="log-entry">
        <strong>{{ entry.title }}</strong><br>
        <span class="typewriter-text-content" :class="{ 'check-mark': entry.isComplete }" v-html="entry.contentHtml"></span>
      </div>
       <div v-if="isProcessing && logEntries.length === 0" class="log-entry">
            <strong>Connecting...</strong><br><span>Waiting for first log entry from backend...</span>
       </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, nextTick } from 'vue';
import type { Ref } from 'vue';

// Interface for log entries
export interface LogEntry {
  title: string;
  content: string;
  contentHtml: string;
  isComplete: boolean;
}

const props = defineProps<{
  logEntries: LogEntry[];
  progressBarWidth: number;
   isProcessing: boolean; // Needed for simplified status message
}>();

const logRef: Ref<HTMLElement | null> = ref(null);

// --- FIX: Move scrollToBottom declaration BEFORE the watch ---
const scrollToBottom = () => {
  if (logRef.value) {
    // Use nextTick here as well to ensure the DOM is updated right before scrolling
    nextTick(() => {
      if (logRef.value) { // Check again inside nextTick
           logRef.value.scrollTop = logRef.value.scrollHeight;
      }
    });
  }
};
// --- End FIX ---


// Watch logEntries array for changes
watch(() => props.logEntries, () => {
  // Now scrollToBottom is declared and can be safely called
  // The nextTick inside scrollToBottom handles waiting for DOM updates
  scrollToBottom();
}, { deep: true, immediate: true });


</script>