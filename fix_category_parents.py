import asyncio
import os
from dotenv import load_dotenv
from supabase import create_client, AsyncClient
from loguru import logger
from slugify import slugify

# --- Настройка ---
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Учетные данные Supabase не найдены в файле .env")

supabase: AsyncClient = create_client(SUPABASE_URL, SUPABASE_KEY)

def generate_slug(text):
    """Генерирует slug из текста."""
    return slugify(text, replacements=[['+', '-plus-'], ['/', '-or-'], ['(', ''], [')', '']])

async def fix_missing_parents():
    """
    Находит родительские категории, которые не существуют как отдельные записи,
    создает их, а затем обновляет их счетчики закладок.
    """
    logger.info("Запуск скрипта для исправления отсутствующих родительских категорий...")

    # 1. Получаем все категории
    try:
        response = supabase.table("categories").select("name, parent_category, bookmarks_count").execute()
        if not response.data:
            logger.warning("Таблица категорий пуста. Исправлять нечего.")
            return
        all_categories = response.data
    except Exception as e:
        logger.error(f"Не удалось получить категории: {e}")
        return

    # 2. Определяем существующие имена и требуемые имена родителей
    existing_category_names = {cat['name'] for cat in all_categories}
    required_parent_names = {cat['parent_category'] for cat in all_categories if cat['parent_category']}

    # 3. Находим родителей, которые отсутствуют в таблице категорий
    missing_parent_names = required_parent_names - existing_category_names

    if not missing_parent_names:
        logger.success("Отсутствующие родительские категории не найдены. База данных в порядке.")
        return

    # 4. Создаем отсутствующие родительские категории
    logger.info(f"Найдено {len(missing_parent_names)} отсутствующих родителей: {missing_parent_names}")
    parents_to_insert = []
    for name in missing_parent_names:
        parents_to_insert.append({
            "name": name,
            "slug": generate_slug(name),
            "parent_category": None,  # Они становятся категориями верхнего уровня
            "bookmarks_count": 0      # Временно ставим 0, обновим позже
        })

    try:
        response = supabase.table("categories").upsert(parents_to_insert).execute()
        if response.data:
            logger.success(f"Успешно вставлено {len(response.data)} отсутствующих родительских категорий.")
        else:
            raise Exception("Операция upsert не вернула данных.")
    except Exception as e:
        logger.error(f"Не удалось вставить отсутствующих родителей: {e}")
        return  # Останавливаемся, если не можем их вставить

    # 5. Обновляем счетчики для вновь созданных родителей
    logger.info("Обновление счетчиков закладок для новых родительских категорий...")
    for parent_name in missing_parent_names:
        # Суммируем счетчики всех дочерних элементов этого родителя
        children_sum = sum(
            cat.get('bookmarks_count', 0) or 0
            for cat in all_categories
            if cat.get('parent_category') == parent_name
        )

        logger.info(f"Обновление счетчика для '{parent_name}' на {children_sum}...")
        try:
            supabase.table("categories").update({"bookmarks_count": children_sum}).eq("name", parent_name).execute()
        except Exception as e:
            logger.error(f"Не удалось обновить счетчик для '{parent_name}': {e}")

    logger.success("Скрипт завершил работу.")


async def main():
    await fix_missing_parents()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nПрограмма прервана пользователем (Ctrl+C)")
    except Exception as e:
        logger.exception("Произошла глобальная ошибка в работе программы:")
