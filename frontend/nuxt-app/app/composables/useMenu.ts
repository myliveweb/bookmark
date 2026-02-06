import { useSupabaseClient } from '#imports'
import type { Database } from '~/../../database.types'

export const useMenu = () => {
  const client = useSupabaseClient<Database>()

  const getMenu = async () => {
    const { data: categories, error } = await client
      .from('categories')
      .select('*, bookmarks_count') // Добавляем bookmarks_count в выборку
      .gt('bookmarks_count', 0) // Фильтруем категории, у которых есть закладки
      .order('name', { ascending: true })

    if (error) {
      console.error('Error fetching categories:', error)
      return []
    }

    const categoryMap = new Map()
    const menu = []

    // First pass: create a map of all categories by their name, ensuring they have bookmarks
    categories.forEach(category => {
      // Только если bookmarks_count > 0, добавляем в карту
      if (category.bookmarks_count && category.bookmarks_count > 0) {
        categoryMap.set(category.name, { ...category, children: [] })
      }
    })

    // Second pass: build the hierarchy, only with categories that have bookmarks
    categoryMap.forEach(category => {
      // Проверяем, существует ли родительская категория в отфильтрованной map
      if (category.parent_category && categoryMap.has(category.parent_category)) {
        const parent = categoryMap.get(category.parent_category)
        // Добавляем дочернюю категорию только если у нее самой есть закладки (уже отфильтровано выше)
        parent.children.push(category)
      } else if (!category.parent_category) { // Только если это корневая категория
        menu.push(category)
      }
    })

    // Удаляем детей, у которых нет bookmarks_count или он равен 0
    menu.forEach(parent => {
        if (parent.children && parent.children.length > 0) {
            parent.children = parent.children.filter(child => child.bookmarks_count && child.bookmarks_count > 0);
        }
    });

    return menu
  }

  return {
    getMenu,
  }
}
