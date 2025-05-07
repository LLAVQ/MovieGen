<template>
  <div class="input-wrapper">
    <div class="input-area">
      <label for="fileUpload" class="morph-label"></label>
      <input
        type="file"
        id="fileUpload"
        accept=".pdf,.doc,.docx,.jpg,.png"
        multiple
        @change="handleFileChange"
        ref="fileInputRef"
      />
      <input
        type="text"
        class="text-input"
        placeholder="Напишите ваш комментарий..."
        :value="modelValue"
        @input="$emit('update:modelValue', ($event.target as HTMLInputElement).value)"
        :disabled="isProcessing"
      />
      <div class="send-icon" @click="sendMessage" v-if="!isProcessing">
        <i class="fas fa-paper-plane"></i>
      </div>
      <div class="stop-icon" @click="stopProcessing" v-if="isProcessing">
        <i class="fas fa-stop"></i>
      </div>
    </div>
  </div>
  <div class="attachment-preview">{{ attachmentPreviewText }}</div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue';
import type { Ref } from 'vue';

const props = defineProps<{
  modelValue: string; // For v-model on text input
  isProcessing: boolean;
}>();

const emit = defineEmits(['update:modelValue', 'files-selected', 'send', 'stop']);

const fileInputRef: Ref<HTMLInputElement | null> = ref(null);
const selectedFiles: Ref<FileList | null> = ref(null); // Internal state for selected files

const attachmentPreviewText = computed(() => {
  if (!selectedFiles.value || selectedFiles.value.length === 0) {
    return 'No file attached';
  } else if (selectedFiles.value.length <= 5) {
    return `Files attached (${selectedFiles.value.length}): ${Array.from(selectedFiles.value).map(f => f.name).join(', ')}`;
  } else {
    return `${selectedFiles.value.length} files attached ✅`;
  }
});

const handleFileChange = (event: Event) => {
  const target = event.target as HTMLInputElement;
  if (target.files) {
    selectedFiles.value = target.files; // Update internal state
    emit('files-selected', selectedFiles.value); // Emit to parent
  }
};

const sendMessage = () => {
  // Basic validation (can add more sophisticated validation if needed)
  if (!props.modelValue.trim() && (!selectedFiles.value || selectedFiles.value.length === 0)) {
    alert("Введите текст или выберите файл");
    return;
  }
  // Emit send event with current text and files
  emit('send', { text: props.modelValue.trim(), files: selectedFiles.value });

  // Note: Clearing inputs is handled in App.vue after sending via WS
};

const stopProcessing = () => {
  // Emit stop event
  emit('stop');
   // Note: Frontend state update (isProcessing, hiding analysis) is handled in App.vue
};

// No input clearing needed here, App.vue handles it after WS send

</script>

<style scoped>
/* Add component-specific styles here if needed */
/* Otherwise, rely on global styles. */
</style>