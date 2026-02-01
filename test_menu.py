import asyncio
import os
import json
from dotenv import load_dotenv
from supabase import create_client, AsyncClient
from loguru import logger
from slugify import slugify

# --- Настройка Supabase ---
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Supabase credentials not found in .env file")
supabase: AsyncClient = create_client(SUPABASE_URL, SUPABASE_KEY)

async def get_categories():
    """
    Получает "VPN" из базы данных.
    """
    logger.info("Fetching categories from the database...")
    response = supabase.table("bookmarks").select("categories").contains("categories", '["Python"]').is_("is_processed", True).execute()
    print(response.data)
    if response.data:
        logger.success(f"Successfully fetched {len(response.data)} records with categories.")
        return [item['categories'] for item in response.data]
    else:
        logger.warning("No categories found.")
        return []

async def main():
    """
    Основная функция.
    """
    categories_list = await get_categories()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nПрограмма прервана пользователем (Ctrl+C)")
    except Exception as e:
        logger.exception("Произошла глобальная ошибка в работе программы:")