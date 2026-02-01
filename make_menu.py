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

# Ограничение на количество закладок для обработки
FETCH_LIMIT = 1000
OUTPUT_FILE = "public/menu.json"

def generate_slug(text):
    """
    Генерирует slug из текста.
    """
    return slugify(text, replacements=[['+', '-plus-'], ['/', '-or-'], ['(', ''], [')', '']])

async def get_categories():
    """
    Получает все категории из базы данных.
    """
    logger.info("Fetching categories from the database...")
    response = supabase.table("bookmarks").select("categories").not_.is_("categories", "null").is_("is_processed", True).execute()
    if response.data:
        logger.success(f"Successfully fetched {len(response.data)} records with categories.")
        return [item['categories'] for item in response.data]
    else:
        logger.warning("No categories found.")
        return []

def process_categories(categories_list):
    """
    Обрабатывает список категорий, чтобы получить уникальные значения.
    """
    if not categories_list:
        return []
    
    all_categories = [category for sublist in categories_list for category in sublist]
    unique_categories = sorted(list(set(all_categories)))
    logger.info(f"Found {len(unique_categories)} unique categories.")
    return unique_categories

def create_menu_structure(unique_categories):
    """
    Создает структуру меню из списка уникальных категорий.
    """
    menu = []
    for category in unique_categories:
        menu.append({
            "title": category,
            "slug": generate_slug(category)
        })
    logger.info("Menu structure created.")
    return menu

def save_menu_to_json(menu):
    """
    Сохраняет меню в JSON-файл.
    """
    # Убедимся, что директория 'public' существует
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(menu, f, ensure_ascii=False, indent=2)
    logger.success(f"Menu successfully saved to {OUTPUT_FILE}")

async def main():
    """
    Основная функция для создания и сохранения меню.
    """
    categories_list = await get_categories()
    unique_categories = process_categories(categories_list)
    menu = create_menu_structure(unique_categories)
    save_menu_to_json(menu)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nПрограмма прервана пользователем (Ctrl+C)")
    except Exception as e:
        logger.exception("Произошла глобальная ошибка в работе программы:")