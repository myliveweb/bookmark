<script setup lang="ts">
import { cn } from '@/lib/utils'

const props = defineProps<{
  src: string
  alt?: string
  class?: string
}>()
</script>

<template>
  <div :class="cn('-mx-4 mt-4 overflow-hidden', props.class)">
    <img :src="src" :alt="alt" class="w-full h-auto object-cover" />
  </div>
</template>