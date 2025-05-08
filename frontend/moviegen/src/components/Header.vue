<template>
  <header>
    <div class="logo poem-animation-container">

      <div
        v-if="currentPieceObject !== null"
        :key="`piece-${currentPieceIndex}`"
        class="poem-piece current-piece"
        :style="currentPieceStyle"
      >
        <pre>{{ currentPieceObject }}</pre>
      </div>

      <div
        v-if="nextPieceObject !== null"
         :key="`piece-${nextPieceIndex}`"
        class="poem-piece next-piece"
        :style="nextPieceStyle"
      >
         <pre>{{ nextPieceObject }}</pre>
      </div>

       <div v-if="!pieces.value || pieces.value.length <= 1" class="poem-piece static">
       </div>

    </div>
  </header>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, nextTick, computed } from 'vue';

// Define the full poem text
const fullPoem = `Помните! Через века, через года, — помните!
О тех, кто уже не придет никогда, — помните!
Не плачьте! В горле сдержите стоны, горькие стоны.
Памяти павших будьте достойны! Вечно достойны!
Хлебом и песней, мечтой и стихами, жизнью просторной,
Каждой секундой, каждым дыханьем будьте достойны!
Люди! Покуда сердца стучатся, — помните!
Какою ценой завоевано счастье, — пожалуйста, помните!
Песню свою отправляя в полет, — помните!
О тех, кто уже никогда не споет, — помните!
Детям своим расскажите о них, чтоб запомнили!
Детям детей расскажите о них, чтобы тоже запомнили!
Во все времена бессмертной Земли помните!
К мерцающим звездам ведя корабли, — о погибших помните!
Встречайте трепетную весну, люди Земли.
Убейте войну, прокляните войну, люди Земли!
Мечту пронесите через года и жизнью наполните!..
Но о тех, кто уже не придет никогда, — заклинаю, — помните!
Роберт Рождественский`;

// Parse the poem into pieces based on punctuation followed by optional space or newline
// Wrap the result in ref() to make it reactive.
const pieces = ref(fullPoem.split(/(?<=[.!?;\n])\s*/).filter(piece => piece.trim() !== ''));
// Add a check in case the split/filter results in an empty array but the original text had content
if (pieces.value.length === 0 && fullPoem.trim().length > 0) {
    // Fallback: if splitting failed but text is not empty, treat the whole poem as one piece
     pieces.value = [fullPoem];
}


// State for animation indices
// Initialize based on the actual number of pieces
const currentPieceIndex = ref(0);
// Start the next piece index, handle case with <= 1 piece
const nextPieceIndex = ref(pieces.value && pieces.value.length > 1 ? 1 : 0);


// Dynamic styles for animation (bound via v-bind:style)
// These will be updated in the script to control transitions
const currentPieceStyle = ref({});
const nextPieceStyle = ref({});

// Animation timing constants (adjust these values to fine-tune the animation look and speed)
const pieceDelay = 3000; // 0.5 seconds delay between pieces starting their transition
const animationDuration = 800; // Milliseconds for the CSS transition of each piece

// To hold the timeout ID for cleanup
let animationTimeout: number | undefined;

// --- Computed Properties to get the piece text string based on index ---
// These access the reactive 'pieces' array using .value safely
const currentPieceObject = computed(() => {
  // Safely check if pieces.value exists and has an element at the current index
  return pieces.value && pieces.value.length > 0 && currentPieceIndex.value < pieces.value.length
         ? pieces.value[currentPieceIndex.value]
         : null; // Return null if the piece doesn't exist (e.g., empty array or invalid index)
});

const nextPieceObject = computed(() => {
  // Safely check if pieces.value exists and has an element at the next index
  return pieces.value && pieces.value.length > 1 && nextPieceIndex.value < pieces.value.length
         ? pieces.value[nextPieceIndex.value]
         : null; // Return null if the piece doesn't exist
});
// --- End Computed Properties ---


// Function to trigger one step of the animation (current piece animates out, next piece animates in)
const advancePoem = async () => {
  // If there's 1 or fewer pieces, nothing to animate.
  if (!pieces.value || pieces.value.length <= 1) return;

  // --- Trigger the animation transition ---
  // These style updates will cause the CSS transitions to run over animationDuration

  // Animate the current piece out (move up, fade out, blur)
  currentPieceStyle.value = {
    ...currentPieceStyle.value, // Keep existing transition property
    opacity: 0,
    transform: 'translateY(-80px)', // Move upwards (adjust value based on header height/font size)
    filter: 'blur(10px)', // Apply blur effect
  };

  // Animate the next piece in (move to center, fade in, unblur)
  nextPieceStyle.value = {
    ...nextPieceStyle.value, // Keep existing transition property
    opacity: 1,
    transform: 'translateY(0px)', // Move to the center position (0px offset from its natural position)
    filter: 'blur(0px)', // Remove blur effect
  };


  // --- Schedule the state update and preparation for the next animation ---
  // Wait for the animation duration to complete before changing indices and resetting styles
  // This timeout fires AFTER the animation finishes (after `animationDuration` milliseconds).
  animationTimeout = setTimeout(async () => {
    // --- Update Indices ---
    // The piece that just finished entering (with index `nextPieceIndex.value`) is now the new 'current' piece index.
    currentPieceIndex.value = nextPieceIndex.value;
    // Calculate the index of the piece that will be 'next' in the sequence (looping back to 0 if needed)
    nextPieceIndex.value = (nextPieceIndex.value + 1) % pieces.value.length;

    // --- Reset Styles for the Next Animation Cycle (Instantly, no transition) ---
    // The new 'current' piece (which just finished entering) needs its style reset
    // to the default visible state (opacity 1, translateY 0, blur 0) instantly,
    // so it's ready to be animated OUT in the *next* advancePoem call.
    currentPieceStyle.value = {
         opacity: 1,
         transform: 'translateY(0px)',
         filter: 'blur(0px)',
         transition: 'none', // Crucial: Remove transition property for instant reset
    };

    // The new 'next' piece (which is about to be 'next' in the *next* cycle) needs its style
    // reset to its starting state (opacity 0, blurred, positioned below the center) instantly,
    // so it's ready to be animated IN in the *next* advancePoem call.
    nextPieceStyle.value = {
         opacity: 0,
         transform: 'translateY(80px)', // Position below center (adjust value)
         filter: 'blur(10px)', // Apply blur effect
         transition: 'none', // Crucial: Remove transition property for instant reset
    };

    // Use await nextTick() after setting transition: 'none' to ensure the style reset
    // is applied to the DOM before we re-add the transition property. This prevents
    // an unwanted animation from the reset point.
    await nextTick();

    // --- Re-add Transitions for the Next Animation Cycle ---
    // Add the transition property back to the styles after the instant reset.
    // Now, when the opacity/transform/filter properties are changed in the *next* advancePoem call,
    // the changes will be animated smoothly.
    const transitionStyle = `opacity ${animationDuration}ms ease, transform ${animationDuration}ms ease, filter ${animationDuration}ms ease`;
    currentPieceStyle.value.transition = transitionStyle;
    nextPieceStyle.value.transition = transitionStyle;

    // --- Schedule the start of the next animation cycle ---
    // The animation loop function ('loop') will handle calling advancePoem again after the delay.

  }, animationDuration); // This timeout waits for the animation transition (`animationDuration`) to finish
};

// --- Animation Loop Control ---
const startAnimationLoop = () => {
    // If there's 1 or fewer pieces after parsing, display the static fallback and stop the animation loop.
    if (!pieces.value || pieces.value.length <= 1) {
         console.warn("Poem has 1 or fewer pieces after parsing. Animation skipped.");
         // Ensure the single piece is visible if it wasn't already
          currentPieceStyle.value = {
              opacity: 1, transform: 'translateY(0px)', filter: 'blur(0px)', transition: 'none'
          };
          nextPieceStyle.value = { opacity: 0, transition: 'none' }; // Hide the 'next' piece
         return; // Stop the function here, do not proceed to animation loop
    };

    // Use a recursive function with setTimeout to control timing and looping
    const loop = () => {
        // Trigger one animation step (current piece out, next piece in)
        advancePoem();

        // Schedule the next call to the 'loop' function.
        // The `pieceDelay` (0.5 seconds) is the desired interval between each piece *starting* its animation.
        // So, we schedule the next call to `loop` after `pieceDelay` has passed since the *previous* call to `loop` started.
        animationTimeout = setTimeout(loop, pieceDelay);
    };

    // --- Initial Setup Before Starting the Loop ---
    // Set the initial styles for the very first piece (index 0) to be visible and centered instantly.
    currentPieceStyle.value = {
         opacity: 1,
         transform: 'translateY(0px)', // Centered position
         filter: 'blur(0px)', // No blur
         transition: 'none', // Crucial: No transition on initial render state
    };
    // Set the initial styles for the second piece (index 1) to be invisible, blurred, and positioned below the center, instantly.
    nextPieceStyle.value = {
         opacity: 0,
         transform: 'translateY(80px)', // Position below center (adjust this value to set the starting point)
         filter: 'blur(10px)', // Apply blur
         transition: 'none', // Crucial: No transition on initial render state
    };

    // Use await nextTick() after applying the initial styles instantly.
    // This waits for Vue to update the DOM with these initial styles BEFORE we add the transition property back.
    // If we add the transition property too soon, the instant style change will be animated.
    nextTick(() => {
         // Re-add the transition property to the styles *after* the initial state is rendered instantly.
         // Now, when the properties (opacity, transform, filter) are changed in the subsequent `advancePoem` calls,
         // the changes will be animated smoothly over the `animationDuration`.
         const transitionStyle = `opacity ${animationDuration}ms ease, transform ${animationDuration}ms ease, filter ${animationDuration}ms ease`;
         currentPieceStyle.value.transition = transitionStyle;
         nextPieceStyle.value.transition = transitionStyle;

         // Start the animation loop by calling the loop function.
         // The first call to 'loop' will trigger the first animation step via advancePoem,
         // and then schedule the next call after `pieceDelay`.
         loop(); // Call the loop function to begin the animation cycle
    });
};


// --- Lifecycle Hooks ---
// Start the animation loop when the component is mounted to the DOM.
onMounted(() => {
  console.log("Header mounted. Starting poem animation loop.");
  startAnimationLoop();
});

// Clean up the timeout when the component is unmounted to prevent memory leaks.
// This is important if the Header component might be removed from the DOM (e.g., routing).
onUnmounted(() => {
  console.log("Header unmounted. Cleaning up poem animation timeout.");
  if (animationTimeout !== undefined) {
    clearTimeout(animationTimeout);
  }
});
</script>

<style scoped>
/* Keep header positioning from global styles */
header {
  position: fixed; /* Already in global */
  top: 20px;       /* Already in global */
  left: 30px;      /* Already in global */
  z-index: 1000;   /* Already in global */
  font-size: 16px; /* Adjust font size for the poem text */
  color: white;    /* Ensure text is visible */
  cursor: default; /* Change cursor from pointer to default */
  overflow: hidden; /* Crucial: Hides parts of the poem outside the header's fixed height */
  height: 120px; /* Set a fixed height for the header area to contain the scrolling */
  width: 300px; /* Set a fixed width for the header area */
}

/* Container for the animated poem pieces */
/* This div acts as the viewport where the pieces animate */
.logo.poem-animation-container {
   /* This div is inside the <header> */
    height: 100%; /* Make the container fill the height of the header */
    overflow: hidden; /* Ensure overflow is hidden */
    position: relative; /* Needed for absolute positioning of poem pieces within it */
    /* Remove any original .logo styles from global CSS that don't apply here */
    font-weight: normal; /* Override potential bold from global .logo */
    transition: none; /* Remove potential transition from global .logo */
}

/* Style for individual poem pieces */
/* These styles define the base appearance and positioning for pieces during animation */
.poem-piece {
    position: absolute; /* Position pieces absolutely within the .poem-animation-container */
    left: 0; /* Align to the left */
    width: 100%; /* Make the piece fill the width of the container, allowing text wrapping */
    white-space: pre-wrap; /* Preserve line breaks and spacing from the <pre> tag */
    line-height: 1.6; /* Adjust line spacing for readability */
    margin: 0; /* Remove default margin from <pre> */
    padding: 0 10px; /* Add some padding on the sides for spacing, adjust as needed */
    box-sizing: border-box; /* Include padding in the element's total width */


    /* Center the text vertically within the header height */
    /* This positioning is overridden by the translateY animation during transitions */
    top: 50%; /* Start at 50% from the top of the container */
    transform: translateY(-50%); /* Move up by half of its own height to truly center it */

    /* Base state (visible, no blur, opacity 1, centered transform) */
    /* Starting blurred/hidden state (opacity 0, blur 10px, translateY 80px) */
    /* These states are controlled by inline styles updated by the script */
    /* Define default appearance if inline styles aren't applied (though they should be) */
    opacity: 1;
    filter: blur(0);
    /* Transition properties are applied via inline styles from JS */

     /* Ensure text is centered horizontally too */
    text-align: center;
}

/* Override base poem-piece styles for the 'current-piece' and 'next-piece' during animation */
/* These classes are used in the template for clarity, but the dynamic styles */
/* bound via :style="" are what directly control the animation state and transitions */
/* The 'current-piece' and 'next-piece' classes themselves don't strictly need specific CSS rules here, */
/* as their appearance is driven by the inline styles. */


/* Style for the static piece when only one piece exists (fallback) */
/* This style applies only to the div with class 'poem-piece static' */
.poem-piece.static {
    position: relative; /* Use relative or static positioning for the fallback */
    opacity: 1;
    transform: translateY(0); /* Reset transform for static content */
    filter: blur(0);
    transition: none; /* Ensure no transition on the static piece */

     /* Center the static text within the header container */
    top: auto; /* Remove the top: 50%; */
    transform: none; /* Remove the translateY(-50%); */
    display: flex; /* Use flexbox for centering */
    justify-content: center; /* Center horizontally */
    align-items: center; /* Center vertically */
    height: 100%; /* Make the div fill the container height for centering to work */
}


/* No CSS @keyframes needed for this JS-driven animation */

</style>