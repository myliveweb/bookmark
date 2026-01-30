<script setup lang="ts">
import { useTheme } from '~/composables/useTheme';

// Initialize the theme management. The composable will watch for changes
// and apply the correct class to the body.
useTheme();
</script>

<template>
  <NuxtLayout>
    <NuxtPage />
  </NuxtLayout>
</template>
