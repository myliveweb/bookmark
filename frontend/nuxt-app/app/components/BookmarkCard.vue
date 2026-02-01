<script setup lang="ts">
import { computed, ref } from 'vue'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '~/components/ui/card'
import CardImage from '~/components/ui/card/CardImage.vue'
import { Eye, Pencil, Trash } from 'lucide-vue-next'
import { Popover, PopoverContent, PopoverTrigger } from '~/components/ui/popover'
import { Button } from '~/components/ui/button'
import { useCenterPosition } from '~/composables/use_center_position'

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
  const supabaseUrl = 'http://127.0.0.1:54321/storage/v1/object/public/screenshots';
  if (!props.bookmark.id) return `${supabaseUrl}/image/102.png`; // Fallback with a default image id, assuming 102.png is a valid default
  return `${supabaseUrl}/image/${props.bookmark.id}.png`;
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

const detailedViewPopover = ref(null)
const { style: detailedViewStyle } = useCenterPosition(detailedViewPopover)
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
            <div data-slot="toggle-group" data-spacing="0" style="--gap:0;outline:none;" spacing="0" class="group/toggle-group flex w-fit items-center rounded-md data-[spacing=default]:data-[variant=outline]:shadow-xs gap-1 *:data-[slot=toggle-group-item]:!size-6 *:data-[slot=toggle-group-item]:!rounded-sm main-block" tabindex="0" dir="ltr" role="group">
              <Popover>
                <PopoverTrigger as-child>
                  <button data-slot="button" class="eye-btn inline-flex items-center justify-center gap-2 whitespace-nowrap text-sm font-medium transition-all disabled:pointer-events-none disabled:opacity-50 [&amp;_svg]:pointer-events-none [&amp;_svg:not([class*='size-'])]:size-4 shrink-0 [&amp;_svg]:shrink-0 outline-none focus-visible:border-ring focus-visible:ring-ring/50 focus-visible:ring-[3px] aria-invalid:ring-destructive/20 dark:aria-invalid:ring-destructive/40 aria-invalid:border-destructive hover:bg-accent hover:text-accent-foreground dark:hover:bg-accent/50 size-6 rounded-sm p-0" title="Refresh Preview">
                    <Eye class="h-4 w-4 trash" />
                    <span class="sr-only">Детальный просмотр</span>
                  </button>
                </PopoverTrigger>
                <PopoverContent :style="detailedViewStyle">
                  <div ref="detailedViewPopover">
                    Детальный просмотр
                  </div>
                </PopoverContent>
              </Popover>
              <div data-orientation="vertical" role="none" data-slot="separator" class="bg-border shrink-0 data-[orientation=horizontal]:h-px data-[orientation=horizontal]:w-full data-[orientation=vertical]:h-full data-[orientation=vertical]:w-px !h-4"><!--[--><!--]--></div>
              <Popover>
                <PopoverTrigger as-child>
                  <button data-slot="button" class="pencil-btn inline-flex items-center justify-center gap-2 whitespace-nowrap text-sm font-medium transition-all disabled:pointer-events-none disabled:opacity-50 [&amp;_svg]:pointer-events-none [&amp;_svg:not([class*='size-'])]:size-4 shrink-0 [&amp;_svg]:shrink-0 outline-none focus-visible:border-ring focus-visible:ring-ring/50 focus-visible:ring-[3px] aria-invalid:ring-destructive/20 dark:aria-invalid:ring-destructive/40 aria-invalid:border-destructive hover:bg-accent hover:text-accent-foreground dark:hover:bg-accent/50 size-6 rounded-sm p-0" title="Refresh Preview">
                    <Pencil class="h-4 w-4 trash" />
                    <span class="sr-only">Редактировать</span>
                  </button>
                </PopoverTrigger>
                <PopoverContent>
                  Редактировать
                </PopoverContent>
              </Popover>
              <div data-orientation="vertical" role="none" data-slot="separator" class="bg-border shrink-0 data-[orientation=horizontal]:h-px data-[orientation=horizontal]:w-full data-[orientation=vertical]:h-full data-[orientation=vertical]:w-px !h-4"><!--[--><!--]--></div>
              <Popover>
                <PopoverTrigger as-child>
                  <button data-slot="button" class="trash-btn inline-flex items-center justify-center gap-2 whitespace-nowrap text-sm font-medium transition-all disabled:pointer-events-none disabled:opacity-50 [&amp;_svg]:pointer-events-none [&amp;_svg:not([class*='size-'])]:size-4 shrink-0 [&amp;_svg]:shrink-0 outline-none focus-visible:border-ring focus-visible:ring-ring/50 focus-visible:ring-[3px] aria-invalid:ring-destructive/20 dark:aria-invalid:ring-destructive/40 aria-invalid:border-destructive hover:bg-accent hover:text-accent-foreground dark:hover:bg-accent/50 size-6 rounded-sm p-0" title="Refresh Preview">
                    <Trash class="h-4 w-4 trash" />
                    <span class="sr-only">Удалить</span>
                  </button>
                </PopoverTrigger>
                <PopoverContent>
                  <div class="flex flex-col space-y-2">
                    <p>Вы уверены, что хотите удалить?</p>
                    <div class="flex justify-end space-x-2">
                      <Button variant="outline">Отмена</Button>
                      <Button variant="destructive">Подтверждаю</Button>
                    </div>
                  </div>
                </PopoverContent>
              </Popover>
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
  .btn-box-icon {
    display: flex;
    justify-content: space-between;
    gap: 0.5rem;
  }
  .btn-box-icon > div {
    cursor: pointer;
  }
  /* .btn-box .eye-btn {
    color: hsl(84.8 85.2% 34.5%);
  }
  .btn-box .pencil-btn {
    color: hsl(45.4 93.4% 47.5%);
  }
  .btn-box .trash-btn {
    color: hsl(0 84.2% 60.2%);
  } */
  .text-date {
    font-size: .7rem;
    color: hsl(24.6 95% 53.1%);
  }
  .main-block button:hover {
    background-color: hsl(150deg 2.29% 33.1%);
    color: white;
  }
</style>
