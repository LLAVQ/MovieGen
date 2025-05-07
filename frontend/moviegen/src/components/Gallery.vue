<template>
  <div class="gallery-container" ref="galleryRef">
    <div
      v-for="(statue, index) in statues"
      :key="index"
      class="statue"
      :class="{ center: index === centerIndex }"
    >
      <img :src="statue.url" :alt="'Statue ' + (index + 1)" loading="lazy" /> </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, nextTick } from 'vue';
import type { Ref } from 'vue';

interface Statue {
  url: string;
}

const props = defineProps<{
  statues: Statue[];
}>();

const galleryRef: Ref<HTMLElement | null> = ref(null);
const centerIndex = ref(0);

const updateCenterStatue = () => {
  if (!galleryRef.value) return;

  const containerRect = galleryRef.value.getBoundingClientRect();
  const containerCenterX = containerRect.left + containerRect.width / 2;
  let closest = null;
  let closestDist = Infinity;
  let closestIndex = -1;

  const statueElements = galleryRef.value.querySelectorAll('.statue');

  statueElements.forEach((statueEl, index) => {
    const rect = statueEl.getBoundingClientRect();
    const elementCenterX = rect.left + rect.width / 2;
    const dist = Math.abs(elementCenterX - containerCenterX);

    if (dist < closestDist) {
      closestDist = dist;
      closest = statueEl;
      closestIndex = index;
    }
  });

  if (closestIndex !== -1) {
    centerIndex.value = closestIndex;
  }
};

onMounted(() => {
  // Use nextTick to ensure elements are rendered before calculating positions
  nextTick(() => {
    if (galleryRef.value) {
      galleryRef.value.addEventListener('scroll', updateCenterStatue);
    }
    // Initial update
    updateCenterStatue();
  });
});

onUnmounted(() => {
  if (galleryRef.value) {
    galleryRef.value.removeEventListener('scroll', updateCenterStatue);
  }
});

// Optional: Expose centerIndex if parent needs to know
// defineExpose({
//   centerIndex
// })
</script>

<style scoped>
/* Add component-specific styles here if needed */
/* Otherwise, rely on global styles. */
</style>