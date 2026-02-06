<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { usePopoverState, closePopover } from '~/composables/usePopoverState'
import { useCenterPosition } from '~/composables/use_center_position'
import { useCategories } from '~/composables/useCategories'
import { Card, CardHeader, CardTitle, CardContent, CardDescription, CardFooter } from '~/components/ui/card'
import { Button } from '~/components/ui/button'
import { Input } from '~/components/ui/input'
import { Label } from '~/components/ui/label'
import { Textarea } from '~/components/ui/textarea'
import { Badge } from '~/components/ui/badge'
import { Command, CommandInput, CommandList, CommandEmpty, CommandGroup, CommandItem } from '~/components/ui/command'
import { useSupabaseClient } from '#imports'
import { 
  ExternalLink, Calendar as CalendarIcon, Trash2, X, Save, 
  RefreshCw, Plus, Check, Loader2, Info, Pencil
} from 'lucide-vue-next'
import { format } from 'date-fns'
import { ru } from 'date-fns/locale'

const state = usePopoverState()
const popoverRef = ref(null)
const supabase = useSupabaseClient()
const { categories: allCategories, fetchCategories, createCategory } = useCategories()

// Состояние редактирования
const editData = ref({
  title: '',
  url: '',
  summary: '',
  date_add: null as number | null,
  categories: [] as string[]
})

const isSaving = ref(false)
const isResnapping = ref(false)
const categoryInput = ref('')
const tempImageSrc = ref<string | null>(null)
const pendingTempFilename = ref<string | null>(null)

// Центрирование
const { style } = useCenterPosition(popoverRef)

const bookmark = computed(() => state.value.props.bookmark)
const type = computed(() => state.value.props.type)

// Инициализация данных при открытии
watch(() => state.value.isOpen, (newVal) => {
  if (newVal && bookmark.value) {
    tempImageSrc.value = null 
    pendingTempFilename.value = null // Сбрасываем ожидающий скриншот
    editData.value = {
      title: bookmark.value.title || '',
      url: bookmark.value.url || '',
      summary: bookmark.value.summary || '',
      date_add: bookmark.value.date_add || null,
      categories: [...(bookmark.value.categories || [])]
    }
    fetchCategories()
  }
}, { immediate: true })

// Форматирование даты специально для нативного инпута (YYYY-MM-DD)
const dateInputString = computed({
  get: () => {
    if (!editData.value.date_add) return ''
    const d = new Date(editData.value.date_add * 1000)
    const year = d.getFullYear()
    const month = String(d.getMonth() + 1).padStart(2, '0')
    const day = String(d.getDate()).padStart(2, '0')
    return `${year}-${month}-${day}`
  },
  set: (val: string) => {
    if (!val) {
      editData.value.date_add = null
      return
    }
    const d = new Date(val)
    // Учитываем смещение часового пояса при выборе даты в нативном инпуте
    editData.value.date_add = Math.floor(d.getTime() / 1000)
  }
})

const imageSrc = computed(() => {
  // Если есть временная картинка от реснапа — показываем её в приоритете
  if (tempImageSrc.value) return tempImageSrc.value

  if (!bookmark.value?.id) return ''
  return `http://127.0.0.1:54321/storage/v1/object/public/screenshots/image/${bookmark.value.id}.png?t=${Date.now()}`
})

// Отображение даты текстом (для режима Detail)
function formatDateText(timestamp: number): string {
  if (!timestamp) return '';
  const date = new Date(timestamp * 1000);
  return format(date, "PPP", { locale: ru });
}

// Удаление категории из списка
function removeCategory(cat: string) {
  editData.value.categories = editData.value.categories.filter(c => c !== cat)
}

// Добавление категории
async function addCategory(name: string) {
  const cleanName = name.trim()
  if (!cleanName) return

  if (!editData.value.categories.includes(cleanName)) {
    if (!allCategories.value.includes(cleanName)) {
      await createCategory(cleanName)
    }
    editData.value.categories.push(cleanName)
  }
  categoryInput.value = ''
}

// Фильтрованный список категорий для автокомплита
const filteredCategories = computed(() => {
  const input = categoryInput.value.toLowerCase()
  if (!input) return allCategories.value.filter(c => !editData.value.categories.includes(c))
  return allCategories.value.filter(c => 
    c.toLowerCase().startsWith(input) && !editData.value.categories.includes(c)
  )
})

// Сохранение изменений
async function handleSave() {
  if (!bookmark.value?.id) return
  isSaving.value = true
  
  try {
    // 1. Если был сделан реснап, сначала коммитим скриншот
    if (pendingTempFilename.value) {
      await fetch('http://127.0.0.1:8000/api/commit-screenshot', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          bookmark_id: bookmark.value.id, 
          temp_filename: pendingTempFilename.value 
        })
      })
    }

    // 2. Обновляем данные в Supabase
    const { error } = await supabase
      .from('bookmarks')
      .update({
        title: editData.value.title,
        url: editData.value.url,
        summary: editData.value.summary,
        date_add: editData.value.date_add,
        categories: editData.value.categories
      })
      .eq('id', bookmark.value.id)

    if (error) throw error
    closePopover()
    window.location.reload() 
  } catch (err) {
    console.error('Ошибка сохранения:', err)
  } finally {
    isSaving.value = false
  }
}

// Обновление скриншота через FastAPI
async function handleResnap() {
  if (!bookmark.value?.url || !bookmark.value?.id) return
  isResnapping.value = true
  
  try {
    const response = await fetch('http://127.0.0.1:8000/api/resnap', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ 
        url: editData.value.url,
        bookmark_id: bookmark.value.id 
      })
    })
    
    if (!response.ok) throw new Error('Resnap failed')
    const result = await response.json()
    
    // Сразу показываем временный скриншот
    if (result.temp_url) {
      tempImageSrc.value = result.temp_url
    }
    
    // Сохраняем имя временного файла, но НЕ коммитим его пока
    pendingTempFilename.value = result.temp_filename

  } catch (err) {
    console.error('Ошибка обновления скриншота:', err)
  } finally {
    isResnapping.value = false
  }
}

async function handleDelete() {
  if (!bookmark.value?.id) return
  try {
    const { error } = await supabase.from('bookmarks').delete().eq('id', bookmark.value.id)
    if (error) throw error
    closePopover()
    window.location.reload()
  } catch (err) {
    alert('Ошибка удаления')
  }
}
</script>

<template>
  <div 
    v-if="state.isOpen" 
    class="fixed inset-0 z-[100] bg-black/60 backdrop-blur-sm flex items-center justify-center p-4"
    @click.self="closePopover"
  >
    
    <!-- РЕЖИМ: EDIT -->
    <Card 
      v-if="type === 'edit'" 
      ref="popoverRef" 
      :style="style" 
      class="w-full max-w-[850px] max-h-[95vh] overflow-y-auto shadow-2xl border-2 flex flex-col"
    >
      <CardHeader class="border-b bg-muted/30 py-4">
        <div class="flex justify-between items-center">
          <CardTitle class="text-xl font-bold flex items-center gap-2">
            <Pencil class="h-5 w-5 text-primary" />
            Редактирование закладки
          </CardTitle>
          <Button @click="closePopover" variant="ghost" size="icon">
            <X class="h-5 w-5" />
          </Button>
        </div>
      </CardHeader>

      <CardContent class="p-6 space-y-6">
        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
          
          <!-- Левая колонка: Основные поля -->
          <div class="space-y-4">
            <div class="space-y-2">
              <Label for="title">Заголовок</Label>
              <Input id="title" v-model="editData.title" placeholder="Название закладки" />
            </div>

            <div class="space-y-2">
              <Label for="url">URL</Label>
              <div class="flex gap-2">
                <Input id="url" v-model="editData.url" placeholder="https://..." />
                <Button variant="outline" size="icon" as-child>
                  <a :href="editData.url" target="_blank"><ExternalLink class="h-4 w-4" /></a>
                </Button>
              </div>
            </div>

            <div class="space-y-2">
              <Label>Дата добавления</Label>
              <Input 
                type="date" 
                v-model="dateInputString"
                class="w-full justify-start text-left font-normal cursor-pointer"
              />
            </div>
          </div>

          <!-- Правая колонка: Скриншот и Категории -->
          <div class="space-y-4">
            <Label>Скриншот</Label>
            <div class="relative group rounded-lg overflow-hidden border bg-muted aspect-video">
              <img :src="imageSrc" class="w-full h-full object-cover" alt="Preview" />
              <div class="absolute inset-0 flex items-center justify-center bg-black/10 transition-opacity">
                <Button @click="handleResnap" :disabled="isResnapping" size="sm" class="shadow-lg disabled:opacity-100">
                  <RefreshCw v-if="!isResnapping" class="mr-2 h-4 w-4" />
                  <Loader2 v-else class="mr-2 h-4 w-4 animate-spin" />
                  Обновить
                </Button>
              </div>
            </div>

            <div class="space-y-2">
              <Label>Категории</Label>
              <div class="flex flex-wrap gap-2 p-2 border rounded-md min-h-[42px] bg-background/50">
                <Badge 
                  v-for="cat in editData.categories" 
                  :key="cat" 
                  variant="secondary"
                  class="gap-1 px-2 py-1"
                >
                  {{ cat }}
                  <X @click="removeCategory(cat)" class="h-3 w-3 cursor-pointer hover:text-destructive" />
                </Badge>
                <p v-if="!editData.categories.length" class="text-sm text-muted-foreground py-1">Нет категорий</p>
              </div>
              
              <!-- Умный выбор категорий -->
              <Command v-model:search-term="categoryInput" class="border rounded-md mt-2">
                <CommandInput 
                  v-model="categoryInput" 
                  placeholder="Поиск или создание категории..." 
                  @keydown.enter="addCategory(categoryInput)"
                />
                <CommandList v-show="categoryInput">
                  <CommandEmpty v-if="!allCategories.some(c => c.toLowerCase() === categoryInput.toLowerCase())">
                    <Button @click="addCategory(categoryInput)" variant="ghost" class="w-full justify-start text-primary">
                      <Plus class="mr-2 h-4 w-4" /> Создать "{{ categoryInput }}"
                    </Button>
                  </CommandEmpty>
                  <CommandGroup heading="Существующие">
                    <CommandItem 
                      v-for="cat in filteredCategories" 
                      :key="cat" 
                      :value="cat"
                      @select="addCategory(cat)"
                    >
                      <Check class="mr-2 h-4 w-4 opacity-0 data-[selected]:opacity-100" />
                      {{ cat }}
                    </CommandItem>
                  </CommandGroup>
                  <!-- Кнопка создания в конце списка, если нет точного совпадения -->
                  <div 
                    v-if="categoryInput && !allCategories.some(c => c.toLowerCase() === categoryInput.toLowerCase()) && filteredCategories.length > 0"
                    class="p-1 border-t"
                  >
                    <Button @click="addCategory(categoryInput)" variant="ghost" class="w-full justify-start text-primary text-xs">
                      <Plus class="mr-2 h-3 w-3" /> Создать "{{ categoryInput }}"
                    </Button>
                  </div>
                </CommandList>
              </Command>
            </div>
          </div>
        </div>

        <div class="space-y-2 pt-2">
          <Label for="summary">Описание (Summary)</Label>
          <Textarea id="summary" v-model="editData.summary" rows="6" placeholder="Краткое содержание..." />
        </div>
      </CardContent>

      <CardFooter class="border-t bg-muted/30 py-4 flex justify-between gap-4">
        <Button @click="closePopover" variant="ghost" :disabled="isSaving">Отмена</Button>
        <Button @click="handleSave" :disabled="isSaving" class="px-10">
          <Save v-if="!isSaving" class="mr-2 h-4 w-4" />
          <Loader2 v-else class="mr-2 h-4 w-4 animate-spin" />
          Сохранить изменения
        </Button>
      </CardFooter>
    </Card>

    <!-- РЕЖИМ: DETAIL -->
    <Card 
      v-else-if="type === 'detail'" 
      ref="popoverRef" 
      :style="style" 
      class="w-[90vw] max-w-[800px] max-h-[90vh] overflow-y-auto shadow-2xl border-2"
    >
      <CardHeader class="relative pb-2">
        <div class="flex justify-between items-start gap-4">
          <div class="space-y-1">
            <CardTitle class="text-2xl font-bold leading-tight">{{ bookmark.title }}</CardTitle>
            <CardDescription class="flex items-center gap-2 text-primary text-base">
              <ExternalLink class="h-4 w-4" />
              <a :href="bookmark.url" target="_blank" class="hover:underline">{{ bookmark.url }}</a>
            </CardDescription>
          </div>
          <Button @click="closePopover" variant="ghost" size="icon"><X class="h-5 w-5" /></Button>
        </div>
      </CardHeader>
      <CardContent class="space-y-6 text-lg">
        <div class="rounded-lg overflow-hidden border bg-muted aspect-video">
          <img :src="imageSrc" class="w-full h-full object-cover" alt="Preview" />
        </div>
        <div v-if="bookmark.summary" class="space-y-2">
          <h4 class="font-semibold text-muted-foreground">Описание</h4>
          <p class="leading-relaxed whitespace-pre-wrap">{{ bookmark.summary }}</p>
        </div>

        <!-- Категории и Дата (только чтение) -->
        <div class="space-y-4 pt-4 border-t">
          <div v-if="bookmark.categories?.length" class="flex flex-wrap gap-2">
            <Badge 
              v-for="cat in bookmark.categories" 
              :key="cat" 
              variant="secondary"
              class="px-3 py-1 text-sm font-medium"
            >
              {{ cat }}
            </Badge>
          </div>
          
          <div class="flex items-center gap-2 text-sm text-muted-foreground">
            <CalendarIcon class="h-4 w-4" />
            <span class="font-medium">Добавлено:</span> {{ formatDateText(bookmark.date_add) }}
          </div>
        </div>
      </CardContent>
    </Card>

    <!-- РЕЖИМ: DELETE -->
    <Card v-else-if="type === 'delete'" ref="popoverRef" :style="style" class="w-[450px] shadow-2xl border-destructive/20 border-2">
      <CardHeader>
        <div class="flex items-center gap-3 text-destructive">
          <Trash2 class="h-6 w-6" />
          <CardTitle class="text-xl font-bold uppercase">Удаление</CardTitle>
        </div>
      </CardHeader>
      <CardContent class="space-y-6">
        <p class="text-lg">Вы действительно хотите удалить закладку <br/><span class="font-bold">«{{ bookmark.title }}»</span>?</p>
        <div class="flex justify-end gap-3 pt-2">
          <Button @click="closePopover" variant="outline" class="flex-1">Отмена</Button>
          <Button @click="handleDelete" variant="destructive" class="flex-1"><Trash2 class="mr-2 h-4 w-4" />Удалить</Button>
        </div>
      </CardContent>
    </Card>

  </div>
</template>