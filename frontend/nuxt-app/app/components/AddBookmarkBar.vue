<script setup lang="ts">
import { ref } from 'vue'
import { Input } from '~/components/ui/input'
import { Button } from '~/components/ui/button'
import { Plus, Link2 } from 'lucide-vue-next'
import { openPopover } from '~/composables/usePopoverState'

const url = ref('')

function handleAdd() {
  const cleanUrl = url.value.trim()
  if (!cleanUrl) return
  
  // Простая валидация URL
  if (!cleanUrl.startsWith('http')) {
    alert('Пожалуйста, введите корректный URL (с http:// или https://)')
    return
  }

  // Открываем глобальный поповер в режиме ADD
  openPopover({}, { 
    type: 'add', 
    initialUrl: cleanUrl 
  })
  
  // Сбрасываем инпут
  url.value = ''
}
</script>

<template>
  <div class="flex items-center gap-2 max-w-md w-full ml-auto">
    <div class="relative flex-1">
      <Link2 class="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
      <Input 
        v-model="url" 
        placeholder="Вставьте URL для новой закладки..." 
        class="pl-9 h-10 shadow-sm focus-visible:ring-primary"
        @keydown.enter="handleAdd"
      />
    </div>
    <Button @click="handleAdd" class="h-10 px-4 gap-2 shadow-sm whitespace-nowrap">
      <Plus class="h-4 w-4" />
      Добавить новую закладку
    </Button>
  </div>
</template>
