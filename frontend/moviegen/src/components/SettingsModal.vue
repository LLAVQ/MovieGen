<template>
  <div class="settings-modal" :class="{ active: isVisible }">
    <p><strong>Settings</strong></p>
    <label>
      Video Style:
      <select>
        <option>Realistic</option>
        <option>Animated</option>
        <option>Cartoon</option>
      </select>
    </label>
    </div>
</template>

<script setup lang="ts">
import { defineProps } from 'vue';

const props = defineProps<{
  isVisible: boolean;
}>();
</script>

<style scoped>
/* Add component-specific styles here if needed */
/* Otherwise, rely on global styles. */
</style>