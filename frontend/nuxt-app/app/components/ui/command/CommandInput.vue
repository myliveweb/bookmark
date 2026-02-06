<script setup lang="ts">
import { type HTMLAttributes } from 'vue'
import { ComboboxInput, type ComboboxInputProps, useForwardProps } from 'reka-ui'
import { Search } from 'lucide-vue-next'
import { cn } from '~/lib/utils'

const props = defineProps<ComboboxInputProps & {
  class?: HTMLAttributes['class'],
  modelValue?: string | number
}>()

const emits = defineEmits<{
  (e: 'update:modelValue', payload: string | number): void
}>()

const forwardedProps = useForwardProps(props)
</script>

<template>
  <div class="flex items-center border-b px-3" cmdk-input-wrapper>
    <Search class="mr-2 h-4 w-4 shrink-0 opacity-50" />
    <ComboboxInput
      v-bind="forwardedProps"
      :value="modelValue"
      @input="emits('update:modelValue', ($event.target as HTMLInputElement).value)"
      :class="cn('flex h-11 w-full rounded-md bg-transparent py-3 text-sm outline-none placeholder:text-muted-foreground disabled:cursor-not-allowed disabled:opacity-50', props.class)"
    />
  </div>
</template>