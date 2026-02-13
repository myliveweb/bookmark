<script setup lang="ts">
import { ref } from 'vue'
import { Input } from '~/components/ui/input'
import { Button } from '~/components/ui/button'
import { Plus, Link2, FileDown, Loader2 } from 'lucide-vue-next'
import { openPopover } from '~/composables/usePopoverState'
import { useConveyor } from '~/composables/useConveyor'

const url = ref('')
const fileInput = ref<HTMLInputElement | null>(null)
const isImporting = ref(false)
const { triggerRefresh } = useConveyor()

function handleAdd() {
  const cleanUrl = url.value.trim()
  if (!cleanUrl) return
  
  if (!cleanUrl.startsWith('http')) {
    alert('Пожалуйста, введите корректный URL (с http:// или https://)')
    return
  }

  openPopover({}, { 
    type: 'add', 
    initialUrl: cleanUrl 
  })
  
  url.value = ''
}

const triggerImport = () => {
  fileInput.value?.click()
}

const handleFileUpload = async (event: Event) => {
  const target = event.target as HTMLInputElement
  if (!target.files?.length) return
  
  const file = target.files[0]
  const formData = new FormData()
  formData.append('file', file)
  
  isImporting.value = true
  try {
    const res = await $fetch('/api/bookmarks/import', {
      method: 'POST',
      body: formData
    })
    console.log('Import successful:', res)
    // Пробуждаем индикатор прогресса
    triggerRefresh()
    target.value = ''
  } catch (e) {
    console.error('Import failed:', e)
  } finally {
    isImporting.value = false
  }
}
</script>

<template>
  <div class="flex items-center gap-2 max-w-md w-full ml-auto">
    <!-- Инпут URL -->
    <div class="relative flex-1">
      <Link2 class="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
      <Input 
        v-model="url" 
        placeholder="Вставьте URL для новой закладки..." 
        class="pl-9 h-10 shadow-sm focus-visible:ring-primary"
        @keydown.enter="handleAdd"
      />
    </div>

    <!-- Кнопка Добавить (+) -->
    <Button 
      @click="handleAdd" 
      variant="secondary" 
      size="icon" 
      class="h-10 w-10 shrink-0 shadow-sm"
      title="Добавить закладку"
    >
      <Plus class="h-5 w-5 stroke-[2.5]" />
    </Button>

    <!-- Кнопка Импорт (Файл) -->
    <div class="relative shrink-0">
      <input 
        ref="fileInput"
        type="file" 
        accept=".html" 
        class="hidden" 
        @change="handleFileUpload"
      />
      <Button 
        variant="secondary" 
        size="icon" 
        class="h-10 w-10 shadow-sm"
        @click="triggerImport"
        :disabled="isImporting"
        title="Импортировать из HTML"
      >
        <Loader2 v-if="isImporting" class="h-5 w-5 animate-spin" />
        <FileDown v-else class="h-5 w-5 stroke-[2.5]" />
      </Button>
    </div>
  </div>
</template>
