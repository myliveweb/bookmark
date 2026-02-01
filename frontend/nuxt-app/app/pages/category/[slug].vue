<template>
  <div class="bg-background text-foreground min-h-screen">
    <h1 class="text-3xl font-bold tracking-tight p-4">Bookmarks in Category: {{ categoryName }}</h1>
    <div v-if="pending" class="p-4">
      <p>Loading bookmarks...</p>
    </div>
    <div v-else-if="error" class="p-4">
      <p>Error loading bookmarks: {{ error.message }}</p>
    </div>
    <div v-else class="p-4">
      <p>Found {{ totalBookmarks }} processed bookmarks in this category.</p>
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

<script setup lang="ts">
import { ref, onMounted, computed, watch } from 'vue'
import { useBookmarks } from '~/composables/useBookmarks'
import { useRoute } from 'vue-router'
// import { useSupabaseClient } from '@nuxtjs/supabase' // This import is necessary for useSupabaseClient()
import {
  Pagination,
  PaginationContent,
  PaginationItem,
  PaginationNext,
  PaginationPrevious,
} from '../../components/ui/pagination'

const { getBookmarksByCategory, PAGE_SIZE } = useBookmarks()
const route = useRoute()

const bookmarks = ref<any[]>([])
const pending = ref(true)
const error = ref<Error | null>(null)
const categoryName = ref('')
const currentPage = ref(1)
const totalBookmarks = ref(0)

const totalPages = computed(() => Math.ceil(totalBookmarks.value / PAGE_SIZE))

async function loadCategoryBookmarks(slug: string, page: number) {
  pending.value = true
  error.value = null
  try {
    // Fetch bookmarks
    const { data, count } = await getBookmarksByCategory(slug, page)
    bookmarks.value = data
    totalBookmarks.value = count

    // Fetch category name
    const { data: categoryData } = await useSupabaseClient()
      .from('categories')
      .select('name')
      .eq('slug', slug)
      .single()
    if (categoryData) {
      categoryName.value = categoryData.name
    } else {
      categoryName.value = slug.replace(/-/g, ' ').replace(/\b\w/g, l => l.toUpperCase())
    }
  } catch (e) {
    error.value = e as Error
    console.error('Error in loadCategoryBookmarks:', e)
  } finally {
    pending.value = false
  }
}

onMounted(() => {
  loadCategoryBookmarks(route.params.slug as string, currentPage.value)
})

watch([currentPage, () => route.params.slug], ([newPage, newSlug]) => {
  if (newSlug) {
    loadCategoryBookmarks(newSlug as string, newPage)
  }
})
</script>

<style scoped>
/* Basic styling for the list */
div {
  padding: 2rem;
}
ul {
  list-style: none;
  padding: 0;
}
li {
  margin: 0.5rem 0;
  padding: 0.5rem;
  border: 1px solid #ccc;
  border-radius: 4px;
}
a {
  text-decoration: none;
  color: #007bff;
}
</style>