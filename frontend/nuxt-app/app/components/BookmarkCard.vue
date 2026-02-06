<script setup lang="ts">
import { computed } from 'vue'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '~/components/ui/card'
import CardImage from '~/components/ui/card/CardImage.vue'
import { Eye, Pencil, Trash } from 'lucide-vue-next'
import { openPopover } from '~/composables/usePopoverState'

const props = defineProps<{
  bookmark: {
    id: number;
    title: string;
    url: string;
    summary?: string;
    categories?: string[];
    date_add?: number;
  };
}>()

const imageSrc = computed(() => {
  const supabaseUrl = 'http://127.0.0.1:54321/storage/v1/object/public/screenshots';
  if (!props.bookmark.id) return `${supabaseUrl}/image/102.png`;
  return `${supabaseUrl}/image/${props.bookmark.id}.png`;
})

function formatDate(timestamp: number): string {
  if (!timestamp) return '';
  const date = new Date(timestamp * 1000);
  return date.toLocaleDateString('ru-RU', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  });
}

// Функция для вызова глобального поповера
function handleAction(actionType: string) {
  openPopover({}, { 
    type: actionType, 
    bookmark: props.bookmark 
  });
}
</script>

<template>
  <Card>
    <CardHeader>
      <CardTitle>{{ bookmark.title.length < 100 ? bookmark.title : bookmark.title.slice(0, 100-3) + '...' }}</CardTitle>
      <CardDescription>
        <a :href="bookmark.url" target="_blank" class="text-primary">{{ bookmark.url.split('/')[2] }}</a>
      </CardDescription>
      <div class="btn-box">
        <div>
          <p v-if="bookmark.date_add"  class="text-date">{{ formatDate(bookmark.date_add) }}</p>
        </div>
        <div class="ml-auto flex items-center gap-2">
          <div class="h-8 items-center gap-1.5 rounded-md border p-1 shadow-none">
            <div class="flex w-fit items-center gap-1 main-block">
              <!-- Кнопка Детальный просмотр -->
              <button 
                @click="handleAction('detail')"
                class="eye-btn inline-flex items-center justify-center size-6 rounded-sm transition-all hover:bg-accent"
                title="Детальный просмотр"
              >
                <Eye class="h-4 w-4" />
                <span class="sr-only">Детальный просмотр</span>
              </button>

              <div class="bg-border h-4 w-px"></div>

              <!-- Кнопка Редактировать -->
              <button 
                @click="handleAction('edit')"
                class="pencil-btn inline-flex items-center justify-center size-6 rounded-sm transition-all hover:bg-accent"
                title="Редактировать"
              >
                <Pencil class="h-4 w-4" />
                <span class="sr-only">Редактировать</span>
              </button>

              <div class="bg-border h-4 w-px"></div>

              <!-- Кнопка Удалить -->
              <button 
                @click="handleAction('delete')"
                class="trash-btn inline-flex items-center justify-center size-6 rounded-sm transition-all hover:bg-accent"
                title="Удалить"
              >
                <Trash class="h-4 w-4" />
                <span class="sr-only">Удалить</span>
              </button>
            </div>
          </div>
        </div>
      </div>
    </CardHeader>
    <CardImage class="mt-2" :src="imageSrc" />
    <CardContent>
      <p class="pb-4" v-if="bookmark.summary">{{ bookmark.summary.length < 240 ? bookmark.summary : bookmark.summary.slice(0, 240-3) + '...' }}</p>
      <div v-if="bookmark.categories && bookmark.categories.length">
        <span v-for="category in bookmark.categories" :key="category" class="inline-block bg-secondary text-secondary-foreground rounded-full px-3 py-1 text-sm font-semibold mr-2 mb-2">
          {{ category }}
        </span>
      </div>
    </CardContent>
  </Card>
</template>

<style scoped>
  .btn-box {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-top: -0.5rem;
  }
  .text-date {
    font-size: .7rem;
    color: hsl(24.6 95% 53.1%);
  }
  .main-block button:hover {
    background-color: hsl(150deg 2.29% 33.1%);
    color: white;
  }
</style>