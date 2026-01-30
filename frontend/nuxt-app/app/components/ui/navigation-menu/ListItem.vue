<script setup lang="ts">
import { type HTMLAttributes } from 'vue'
import { NavigationMenuLink } from '~/components/ui/navigation-menu'
import { cn } from '~/lib/utils'

const props = defineProps<{
  class?: HTMLAttributes['class']
  title: string
  to: string
}>()
</script>

<template>
  <li>
    <NavigationMenuLink as-child>
      <a
        :href="to"
        :class="cn(
          'block select-none space-y-1 rounded-md p-2 leading-none no-underline outline-none transition-colors hover:bg-accent hover:text-accent-foreground focus:bg-accent focus:text-accent-foreground',
          props.class,
        )"
      >
        <div class="text-sm font-medium leading-none">{{ title }}</div>
        <p class="line-clamp-2 text-sm leading-snug text-muted-foreground">
          <slot />
        </p>
      </a>
    </NavigationMenuLink>
  </li>
</template>
