import { ref } from 'vue'
import { useRuntimeConfig } from '#app'

export const useCategories = () => {
  const categories = ref<string[]>([])
  const isLoading = ref(false)

  // Получение списка имен категорий из FastAPI
  const fetchCategories = async () => {
    isLoading.value = true
    try {
      // В Nuxt обычно проксируют запросы или используют полный URL
      // Пока используем хардкод URL бэкенда (можно вынести в env позже)
      const response = await fetch('http://127.0.0.1:8000/api/categories')
      const data = await response.json()
      categories.value = data.categories || []
    } catch (error) {
      console.error('Error fetching categories:', error)
    } finally {
      isLoading.value = false
    }
  }

  // Создание новой категории через бэкенд
  const createCategory = async (name: string, contextSlug?: string) => {
    try {
      const response = await fetch('http://127.0.0.1:8000/api/categories', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, context_slug: contextSlug })
      })
      if (!response.ok) throw new Error('Failed to create category')
      const newCat = await response.json()
      
      // Обновляем локальный список
      if (!categories.value.includes(newCat.name)) {
        categories.value.push(newCat.name)
        categories.value.sort()
      }
      return newCat
    } catch (error) {
      console.error('Error creating category:', error)
      return null
    }
  }

  return {
    categories,
    isLoading,
    fetchCategories,
    createCategory
  }
}
