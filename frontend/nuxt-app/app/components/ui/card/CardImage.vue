<template>
  <img :src="src" alt="Card image" class="w-full h-auto" />
</template>

<script setup lang="ts">
defineProps<{
  src: string;
}>();
</script>
