
import { computed } from 'vue'
import { useWindowSize, useElementBounding } from '@vueuse/core'
import type { Ref } from 'vue'

export function useCenterPosition(target: Ref<HTMLElement | null>) {
  const { width: windowWidth, height: windowHeight } = useWindowSize()
  const { width: elementWidth, height: elementHeight } = useElementBounding(target)

  const style = computed(() => {
    const left = (windowWidth.value - elementWidth.value) / 2
    const top = (windowHeight.value - elementHeight.value) / 2
    return {
      position: 'fixed',
      left: `${left}px`,
      top: `${top}px`,
    }
  })

  return {
    style,
  }
}
