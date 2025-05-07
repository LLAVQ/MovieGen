// src/main.ts
import { createApp } from 'vue';
import App from './App.vue';

import './assets/styles.css'; // Import your local global styles (make sure filename is 'styles.css')

// The FontAwesome CDN is now loaded via a <link> tag in index.html
// import 'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css'; // REMOVE or COMMENT OUT this line


createApp(App).mount('#app');