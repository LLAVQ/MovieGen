<template>
  <div class="input-wrapper">
    <textarea
      v-model="inputText"
      placeholder="Напишите ваш комментарий..."
      rows="1"
      @keydown.enter.prevent="handleEnter"
    ></textarea>

    <label for="fileInput" class="file-attach-button">
      <span class="icon">📎</span>
      <input
        id="fileInput"
        type="file"
        multiple
        @change="handleFileChange"
        accept=".pdf,.docx,.txt,.md,.csv" >
    </label>

    <span v-if="selectedFiles.length > 0" class="file-count">
      {{ selectedFiles.length }} file(s) attached
    </span>


    <button @click="handleSend" :disabled="isProcessing || (!inputText.trim() && selectedFiles.length === 0)">
      <span class="icon">▶</span>
    </button>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue';

const inputText = ref('');
const selectedFiles = ref<File[]>([]); // State to hold selected files

// Props for processing state (if needed to disable input/button)
const props = defineProps<{
  isProcessing: boolean;
}>();


// Emit event when send button is clicked or Enter is pressed
const emit = defineEmits(['send']);

const handleSend = () => {
  if (!inputText.value.trim() && selectedFiles.value.length === 0) {
    return; // Don't send if both text and files are empty
  }
  // Emit both text and selected files
  emit('send', { text: inputText.value, files: selectedFiles.value });
  // Clear input and selected files after sending
  inputText.value = '';
  selectedFiles.value = []; // Clear selected files
};

const handleEnter = (event: KeyboardEvent) => {
  // Only send on Enter if Shift is not held (for new line)
  if (!event.shiftKey) {
    handleSend();
  }
  // Allow Shift + Enter for new line (default browser behavior)
};

// Handle file input change
const handleFileChange = (event: Event) => {
    const input = event.target as HTMLInputElement;
    if (input.files) {
        selectedFiles.value = Array.from(input.files); // Store selected files
         console.log("Selected files:", selectedFiles.value);
    } else {
         selectedFiles.value = [];
    }
     // Clear the file input value so the same file can be selected again
     input.value = '';
};

// Optional: Watch selectedFiles to react in the UI
watch(selectedFiles, (newFiles) => {
    console.log(`Number of files selected: ${newFiles.length}`);
    // You could add more logic here, e.g., display file names
});

</script>

<style scoped>
.input-wrapper {
    display: flex;
    align-items: center;
    padding: 10px;
    background-color: #333; /* Dark background */
    border-radius: 25px; /* Pill shape */
    position: fixed; /* Fixed position at the bottom */
    bottom: 20px;
    left: 50%;
    transform: translateX(-50%); /* Center horizontally */
    width: calc(100% - 60px); /* Adjust width */
    max-width: 700px; /* Max width */
    box-shadow: 0 2px 10px rgba(0, 0, 0, 0.5);
    z-index: 1000; /* Ensure it's on top */
}

textarea {
    flex-grow: 1; /* Takes available space */
    margin-right: 10px;
    padding: 10px;
    border: none;
    border-radius: 20px;
    background-color: #444; /* Slightly lighter dark for textarea */
    color: white;
    resize: none; /* Prevent manual resizing */
    overflow-y: auto; /* Add scroll if needed */
    font-size: 1rem;
     min-height: 40px; /* Minimum height */
     max-height: 150px; /* Maximum height before scrolling */
}

 /* Hide the default file input */
input[type="file"] {
    display: none;
}

 .file-attach-button {
    background-color: #555; /* Button background */
    color: white;
    border: none;
    border-radius: 50%; /* Circle button */
    width: 40px; /* Button size */
    height: 40px;
    display: flex;
    justify-content: center;
    align-items: center;
    cursor: pointer;
    margin-right: 10px;
     flex-shrink: 0; /* Prevent shrinking */
     font-size: 1.2rem;
 }

 .file-count {
    color: #bbb; /* Lighter grey text */
    font-size: 0.9rem;
    margin-right: 10px;
    flex-shrink: 0;
 }


button {
    background-color: #007bff; /* Blue send button */
    color: white;
    border: none;
    border-radius: 50%; /* Circle button */
    width: 40px; /* Button size */
    height: 40px;
    display: flex;
    justify-content: center;
    align-items: center;
    cursor: pointer;
    flex-shrink: 0; /* Prevent shrinking */
    font-size: 1.2rem;
     transition: background-color 0.3s ease;
}

button:hover:not(:disabled) {
    background-color: #0056b3; /* Darker blue on hover */
}

button:disabled {
    background-color: #555; /* Grey when disabled */
    cursor: not-allowed;
}
</style>