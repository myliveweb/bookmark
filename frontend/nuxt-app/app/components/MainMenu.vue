<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSub,
  DropdownMenuSubTrigger,
  DropdownMenuSubContent
} from '~/components/ui/dropdown-menu'
import { useMenu } from '~/composables/useMenu'
import { useTheme } from '~/composables/useTheme'
import { Button } from '~/components/ui/button'
import { Sun, Moon, ChevronDown } from 'lucide-vue-next'

const { getMenu } = useMenu()
const allMenuItems = ref([])

onMounted(async () => {
  allMenuItems.value = await getMenu()
})

// Фильтруем только корневые категории (у которых parent_category === null)
// Они уже отсортированы в useMenu и имеют bookmarks_count > 0
const rootCategories = computed(() => {
  return allMenuItems.value.filter(item => item.parent_category === null)
})

const { theme, toggleTheme } = useTheme()
</script>

<template>
  <div class="border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
    <div class="container flex h-16 items-center justify-between">
      <div class="flex items-center gap-8">
        <!-- Текстовый логотип -->
        <NuxtLink to="/" class="flex items-center space-x-2">
          <span class="text-xl font-bold tracking-tight">Bookmark App</span>
        </NuxtLink>

        <!-- Навигационное меню (Dropdown) -->
        <DropdownMenu>
          <DropdownMenuTrigger class="group inline-flex h-10 w-max items-center justify-center rounded-md bg-background px-4 py-2 text-sm font-medium transition-colors hover:bg-accent hover:text-accent-foreground focus:bg-accent focus:text-accent-foreground focus:outline-none disabled:pointer-events-none disabled:opacity-50 data-[active]:bg-accent/50 data-[state=open]:bg-accent/50">
            Категории
            <ChevronDown class="relative top-[1px] ml-1 h-3 w-3 transition duration-200 group-data-[state=open]:rotate-180" aria-hidden="true" />
          </DropdownMenuTrigger>
          <DropdownMenuContent class="w-64" align="start">
            <template v-for="category in rootCategories" :key="category.slug">
              <!-- Если есть подкатегории -->
              <DropdownMenuSub v-if="category.children && category.children.length > 0">
                <DropdownMenuSubTrigger class="cursor-pointer py-2.5">
                  <div class="flex flex-1 items-center justify-between">
                    <span>{{ category.name }}</span>
                    <span class="ml-2 text-xs text-muted-foreground">{{ category.bookmarks_count }}</span>
                  </div>
                </DropdownMenuSubTrigger>
                <DropdownMenuSubContent 
                  :class="[
                    'p-1',
                    category.children.length > 8 ? 'w-[500px] grid grid-cols-2 gap-x-1' : 'w-56'
                  ]"
                >
                  <DropdownMenuItem v-for="child in category.children" :key="child.slug" as-child>
                    <NuxtLink :to="`/category/${child.slug}`" class="flex w-full cursor-pointer items-center justify-between">
                      <span class="truncate">{{ child.name }}</span>
                      <span class="ml-2 text-xs text-muted-foreground">{{ child.bookmarks_count }}</span>
                    </NuxtLink>
                  </DropdownMenuItem>
                </DropdownMenuSubContent>
              </DropdownMenuSub>

              <!-- Если нет подкатегорий -->
              <DropdownMenuItem v-else as-child>
                <NuxtLink :to="`/category/${category.slug}`" class="flex w-full cursor-pointer items-center justify-between py-2.5">
                  <span>{{ category.name }}</span>
                  <span class="ml-2 text-xs text-muted-foreground">{{ category.bookmarks_count }}</span>
                </NuxtLink>
              </DropdownMenuItem>
            </template>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>

      <!-- Переключатель темы справа -->
      <div class="flex items-center">
        <Button @click="toggleTheme" variant="ghost" size="icon" class="h-10 w-10">
          <Sun class="h-[1.2rem] w-[1.2rem] rotate-0 scale-100 transition-all dark:-rotate-90 dark:scale-0" />
          <Moon class="absolute h-[1.2rem] w-[1.2rem] rotate-90 scale-0 transition-all dark:rotate-0 dark:scale-100" />
          <span class="sr-only">Toggle theme</span>
        </Button>
      </div>
    </div>
  </div>
</template>