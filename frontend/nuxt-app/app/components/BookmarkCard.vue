<script setup lang="ts">
import { computed } from 'vue'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '~/components/ui/card'
import CardImage from './ui/card/CardImage.vue';

const props = defineProps<{
  bookmark: {
    id: number;
    title: string;
    url: string;
    summary?: string; // Optional, as it might be null
    categories?: string[]; // Assuming it's an array of strings
    date_add?: number; // Integer, needs formatting
    // Add other relevant fields from your Supabase schema here
  };
}>()

const imageSrc = computed(() => {
  if (!props.bookmark.id) return '/processed_bookmarks/102/screenshot_1280x720.png'
  return `/processed_bookmarks/${props.bookmark.id}/screenshot_1280x720.png`
})

function formatDate(timestamp: number): string {
  if (!timestamp) return '';
  // Convert seconds to milliseconds
  const date = new Date(timestamp * 1000);
  return date.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  });
}
</script>

<template>
  <Card>
    <CardHeader>
      <CardTitle>{{ bookmark.title.length < 100 ? bookmark.title : bookmark.title.slice(0, 97) + '...' }}</CardTitle>
      <CardDescription>
        <a :href="bookmark.url" target="_blank" class="text-primary">{{ bookmark.url.split('/')[2] }}</a>
      </CardDescription>
    </CardHeader>
    <CardContent>
      <p class="pb-4" v-if="bookmark.summary">{{ bookmark.summary }}</p>
      <div v-if="bookmark.categories && bookmark.categories.length">
        <span v-for="category in bookmark.categories" :key="category" class="inline-block bg-secondary text-secondary-foreground rounded-full px-3 py-1 text-sm font-semibold mr-2 mb-2">
          {{ category }}
        </span>
      </div>
      <p v-if="bookmark.date_add">{{ formatDate(bookmark.date_add) }}</p>
    </CardContent>
  </Card>
</template>
