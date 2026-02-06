<script setup lang="ts">
import { ref, onMounted } from 'vue'
import {
  NavigationMenu,
  NavigationMenuContent,
  NavigationMenuItem,
  NavigationMenuLink,
  NavigationMenuList,
  NavigationMenuTrigger,
} from '~/components/ui/navigation-menu'
import ListItem from '~/components/ui/navigation-menu/ListItem.vue'
import { useMenu } from '~/composables/useMenu'
import { useTheme } from '~/composables/useTheme'
import { Button } from '~/components/ui/button'
import { Sun, Moon, Circle } from 'lucide-vue-next'

const { getMenu } = useMenu()
const menuItems = ref([])

onMounted(async () => {
  const allCategories = await getMenu()
  menuItems.value = allCategories.filter(item => item.parent_category === null)
})

const { theme, toggleTheme } = useTheme()
</script>

<template>
  <NavigationMenu class="p-4">
    <NavigationMenuList class="w-full justify-between">
      <div class="flex items-center space-x-4">
        <NavigationMenuItem>
          <NavigationMenuLink href="/" class="flex items-center space-x-2">
            <Circle class="h-6 w-6" />
            <span class="text-lg font-bold">Bookmark App</span>
          </NavigationMenuLink>
        </NavigationMenuItem>

        <NavigationMenuItem v-for="item in menuItems" :key="item.slug">
          <template v-if="item.children && item.children.length > 0">
            <NavigationMenuTrigger>{{ item.name }}</NavigationMenuTrigger>
            <NavigationMenuContent class="z-50 bg-popover shadow-lg">
              <ul class="grid w-[600px] gap-2 p-2 md:w-[700px] md:grid-cols-3 lg:w-[900px]">
                <ListItem
                  v-for="child in item.children"
                  :key="child.slug"
                  :title="child.name"
                  :to="`/category/${child.slug}`"
                />
              </ul>
            </NavigationMenuContent>
          </template>
          <template v-else>
            <NavigationMenuLink :href="`/category/${item.slug}`" class="px-4 py-2">
              {{ item.name }}
            </NavigationMenuLink>
          </template>
        </NavigationMenuItem>
      </div>

      <div>
        <Button @click="toggleTheme" variant="ghost" size="icon">
          <Sun class="h-[1.2rem] w-[1.2rem] rotate-0 scale-100 transition-all dark:-rotate-90 dark:scale-0" />
          <Moon class="absolute h-[1.2rem] w-[1.2rem] rotate-90 scale-0 transition-all dark:rotate-0 dark:scale-100" />
          <span class="sr-only">Toggle theme</span>
        </Button>
      </div>

    </NavigationMenuList>
  </NavigationMenu>
</template>