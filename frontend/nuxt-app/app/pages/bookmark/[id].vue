<template>
  <div>
    <h1>Bookmark Detail Page</h1>
    <p>Loading details for Bookmark ID: {{ bookmarkId }}</p>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const bookmarkId = ref<string | string[]>(route.params.id)

// Later we will fetch bookmark details using bookmarkId

onMounted(() => {
  console.log('Bookmark Detail Page loaded for ID:', bookmarkId.value)
})
</script>

<style scoped>
div {
  padding: 2rem;
  text-align: center;
}
</style>
