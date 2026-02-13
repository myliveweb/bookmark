<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue'
import { Loader2, Check } from 'lucide-vue-next'
import { useConveyor } from '~/composables/useConveyor'

interface Status {
  total: number
  processed: number
  errors: number
}

const { isWorking, stopWorking } = useConveyor()
const status = ref<Status>({ total: 0, processed: 0, errors: 0 })
const showReady = ref(false)
const isVisible = ref(false)
let timer: any = null

const fetchStatus = async () => {
  try {
    // Используем прямой fetch, чтобы избежать интерференции с роутером Nuxt
    const response = await fetch('/api/system/conveyor-status')
    if (!response.ok) return
    const data: Status = await response.json()
    
    // Если работа в процессе
    if (data.total > 0 && data.processed < data.total) {
      status.value = data
      isVisible.value = true
      showReady.value = false
      startTimer() // Убеждаемся, что таймер запущен
    } 
    // Если всё доделано прямо сейчас
    else if (isVisible.value && data.total > 0 && data.processed === data.total) {
      status.value = data
      showReady.value = true
      stopTimer()
      stopWorking() // Сообщаем системе, что мы закончили
      
      setTimeout(() => {
        isVisible.value = false
        showReady.value = false
      }, 3000)
    }
    // Если всё тихо
    else {
      isVisible.value = false
      stopTimer()
      stopWorking()
    }
  } catch (e) {
    stopTimer()
  }
}

const startTimer = () => {
  if (!timer) {
    timer = setInterval(fetchStatus, 5000)
  }
}

const stopTimer = () => {
  if (timer) {
    clearInterval(timer)
    timer = null
  }
}

// Просыпаемся по сигналу
watch(isWorking, (newVal) => {
  if (newVal) {
    isVisible.value = true
    fetchStatus()
    startTimer()
  }
})

onMounted(() => {
  // Первичная проверка при загрузке страницы
  fetchStatus()
})

onUnmounted(() => {
  stopTimer()
})
</script>

<template>
  <Transition
    enter-active-class="transition duration-300 ease-out"
    enter-from-class="transform scale-95 opacity-0"
    enter-to-class="transform scale-100 opacity-100"
    leave-active-class="transition duration-200 ease-in"
    leave-from-class="transform scale-100 opacity-100"
    leave-to-class="transform scale-95 opacity-0"
  >
    <div v-if="isVisible" class="flex items-center gap-3 px-4 py-1.5 bg-accent/40 border border-border/50 backdrop-blur-sm rounded-full shadow-sm">
      <template v-if="!showReady">
        <Loader2 class="w-4 h-4 animate-spin text-primary" />
        <div class="flex items-center gap-2">
          <span class="text-xs font-semibold tabular-nums tracking-tight">
            {{ status.processed }} <span class="text-muted-foreground">/</span> {{ status.total }}
          </span>
          <div v-if="status.errors > 0" class="flex items-center gap-1 px-1.5 py-0.5 bg-destructive/10 rounded text-[10px] text-destructive font-bold uppercase tracking-wider">
            {{ status.errors }} err
          </div>
        </div>
      </template>
      <template v-else>
        <div class="flex items-center gap-2 text-green-500 animate-in zoom-in duration-300">
          <Check class="w-4 h-4" />
          <span class="text-xs font-bold uppercase tracking-wider">Готово</span>
        </div>
      </template>
    </div>
  </Transition>
</template>
