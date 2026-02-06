<script setup lang="ts">
import { type HTMLAttributes, computed } from 'vue'
import { ComboboxEmpty, type ComboboxEmptyProps } from 'reka-ui'
import { cn } from '~/lib/utils'

const props = defineProps<ComboboxEmptyProps & { class?: HTMLAttributes['class'] }>()
</script>

<template>
  <ComboboxEmpty
    v-bind="props"
    :class="cn('py-6 text-center text-sm', props.class)"
  >
    <slot />
  </ComboboxEmpty>
</template>
