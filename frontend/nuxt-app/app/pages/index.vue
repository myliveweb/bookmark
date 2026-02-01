<script setup lang="ts">
import { ref, onMounted, computed, watch } from 'vue'
import { useBookmarks } from '../composables/useBookmarks'
import {
  Pagination,
  PaginationContent,
  PaginationItem,
  PaginationNext,
  PaginationPrevious,
} from '@/components/ui/pagination'

const { getBookmarks, PAGE_SIZE } = useBookmarks()

const bookmarks = ref<any[]>([])
const pending = ref(true)
const error = ref<Error | null>(null)
const currentPage = ref(1)
const totalBookmarks = ref(0)

const totalPages = computed(() => Math.ceil(totalBookmarks.value / PAGE_SIZE))

async function fetchData(page: number) {
  pending.value = true
  error.value = null
  try {
    const { data, count } = await getBookmarks(page)
    bookmarks.value = data
    totalBookmarks.value = count
  }
  catch (e) {
    error.value = e as Error
    console.error('Error fetching bookmarks:', e)
  }
  finally {
    pending.value = false
  }
}

onMounted(() => {
  fetchData(currentPage.value)
})

watch(currentPage, (newPage) => {
  fetchData(newPage)
})
</script>

<template>
  <div class="bg-background text-foreground min-h-screen">
    <h1 class="text-3xl font-bold tracking-tight pl-4">Мои закладки..</h1>
    <div v-if="pending" class="p-4">
      <p>Loading bookmarks...</p>
    </div>
    <div v-else-if="error" class="p-4">
      <p>Error loading bookmarks: {{ error.message }}</p>
    </div>
    <div v-else class="p-4">
      <p class="mb-4">Found {{ totalBookmarks }} processed bookmarks.</p>
      <div class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4 mb-8">
        <BookmarkCard v-for="bookmark in bookmarks" :key="bookmark.id" :bookmark="bookmark" />
      </div>
      <Pagination v-if="totalPages > 1" v-slot="{ page }" @update:page="newPage => currentPage = newPage" :items-per-page="PAGE_SIZE" :total="totalBookmarks" :default-page="currentPage">
      <PaginationContent v-slot="{ items }">
        <PaginationPrevious />
        <template v-for="(item, index) in items" :key="index">
          <PaginationItem
            v-if="item.type === 'page'"
            :value="item.value"
            :is-active="item.value === page"
          >
            {{ item.value }}
          </PaginationItem>
        </template>
        <PaginationEllipsis :index="4" />
        <PaginationNext />
      </PaginationContent>
    </Pagination>
    </div>
  </div>
</template>