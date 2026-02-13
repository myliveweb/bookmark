import { ref } from 'vue'

const isWorking = ref(false)

export const useConveyor = () => {
  const triggerRefresh = () => {
    isWorking.value = true
  }

  const stopWorking = () => {
    isWorking.value = false
  }

  return {
    isWorking,
    triggerRefresh,
    stopWorking
  }
}
