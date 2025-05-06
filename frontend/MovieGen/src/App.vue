<template>
  <div>
    <h1>{{ message }}</h1>
  </div>
</template>

<script>
import axios from 'axios'

export default {
  data() {
    return {
      message: 'Loading...'
    }
  },
  mounted() {
    axios.get('http://localhost:8000/api/hello')
      .then(response => {
        this.message = response.data.message
      })
      .catch(error => {
        this.message = 'Failed to load message from backend.'
        console.error(error)
      })
  }
}
</script>

<style>
h1 {
  font-family: sans-serif;
}
</style>