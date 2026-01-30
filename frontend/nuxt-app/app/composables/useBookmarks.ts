import { useSupabaseClient } from '#imports'
import type { Database } from '~/../../../database.types'

export const useBookmarks = () => {
  const client = useSupabaseClient<Database>()
  const PAGE_SIZE = 16;

  const getBookmarks = async (page = 1) => {
    // Query 1: Get total count
    const { count: totalCount, error: countError } = await client
      .from('bookmarks')
      .select('*', { count: 'exact', head: true })
      .eq('is_processed', true)

    if (countError) {
      console.error('Error fetching total bookmark count:', countError)
      return { data: [], count: 0 }
    }

    // Query 2: Get paginated data
    const { data, error } = await client
      .from('bookmarks')
      .select('*')
      .eq('is_processed', true) // Filter for processed bookmarks
      .order('date_add', { ascending: false })
      .range((page - 1) * PAGE_SIZE, page * PAGE_SIZE - 1)

    if (error) {
      console.error('Error fetching bookmarks:', error)
      return { data: [], count: 0 }
    }

    return { data, count: totalCount ?? 0 }
  }

  const getBookmarksByCategory = async (slug: string, page = 1) => {
    // First, get the category name from the slug
    const { data: categoryData, error: categoryError } = await client
      .from('categories')
      .select('name')
      .eq('slug', slug)
      .single()

    if (categoryError || !categoryData) {
      console.error('Error fetching category:', categoryError)
      return { data: [], count: 0 }
    }

    const categoryName = [categoryData.name]

    // Query 1: Get total count for category
    const { count: totalCount, error: countError } = await client
      .from('bookmarks')
      .select('*', { count: 'exact', head: true })
      .eq('is_processed', true)
      .contains('categories', `"${categoryName}"`)

    if (countError) {
      console.error('Error fetching total bookmark count by category:', countError)
      return { data: [], count: 0 }
    }

    // Then, get the bookmarks that contain this category
    const { data, error } = await client
      .from('bookmarks')
      .select('*')
      .eq('is_processed', true)
      .contains('categories', `"${categoryName}"`)
      .order('date_add', { ascending: false })
      .range((page - 1) * PAGE_SIZE, page * PAGE_SIZE - 1)

    if (error) {
      console.error('Error fetching bookmarks by category:', error)
      return { data: [], count: 0 }
    }

    return { data, count: totalCount ?? 0 }
  }

  return {
    getBookmarks,
    getBookmarksByCategory,
    PAGE_SIZE,
  }
}
