import { ref, watchEffect } from 'vue'

type Theme = 'light' | 'dark'

const theme = ref<Theme>('dark') // Default to dark theme

export function useTheme() {
  function toggleTheme() {
    theme.value = theme.value === 'light' ? 'dark' : 'light'
  }

  watchEffect(() => {
    if (process.client) {
      const body = document.body
      if (theme.value === 'dark') {
        body.classList.add('dark')
      } else {
        body.classList.remove('dark')
      }
    }
  })

  return {
    theme,
    toggleTheme,
  }
}
