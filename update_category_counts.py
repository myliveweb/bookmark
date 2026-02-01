import asyncio
import json
import os
from dotenv import load_dotenv
from supabase import create_client, AsyncClient
from loguru import logger

# --- Настройка Supabase ---
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Supabase credentials not found in .env file")
supabase: AsyncClient = create_client(SUPABASE_URL, SUPABASE_KEY)

async def update_category_counts():
    """
    Подсчитывает и обновляет количество закладок для каждой категории.
    """
    logger.info("Fetching all categories...")
    categories_response = supabase.table("categories").select("id, name").execute()
    if not categories_response.data:
        logger.warning("No categories found.")
        return

    categories = categories_response.data
    logger.info(f"Found {len(categories)} categories. Updating counts...")

    for category in categories:
        category_name = category['name']
        
        # Подсчет закладок для каждой категории
        count_response = supabase.table("bookmarks").select("id", count="exact").contains("categories", f'["{category_name}"]').execute()

        bookmarks_count = 0
        if count_response.count is not None:
            bookmarks_count = count_response.count

        # Обновление счетчика в таблице categories
        supabase.table("categories").update({"bookmarks_count": bookmarks_count}).eq("id", category['id']).execute()
        logger.info(f"Category '{category_name}' updated with count: {bookmarks_count}")

async def main():
    await update_category_counts()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nПрограмма прервана пользователем (Ctrl+C)")
    except Exception as e:
        logger.exception("Произошла глобальная ошибка в работе программы:")
