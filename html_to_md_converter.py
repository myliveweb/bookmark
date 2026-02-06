# html_to_md_converter.py
import os
from loguru import logger
# from markitdown import MarkItDown # Удаляем MarkItDown
from markdownify import markdownify as md # Используем markdownify
import asyncio

# --- Основные настройки ---
PROCESSED_BOOKMARKS_DIR = "frontend/nuxt-app/public/processed_bookmarks"
CONVERT_LIMIT_VALID = 1000000 # Конвертировать все валидные HTML-файлы

# Инициализация markdownify (если нужны параметры, можно передать их здесь)
# md_converter = md(heading_style="ATX", default_title=True)
# В случае markdownify, мы вызываем функцию md(), а не создаем объект
# Поэтому переменная md используется напрямую
# md_converter_instance = md 

async def convert_html_to_md():
    logger.info(f"Начинаем конвертацию HTML в Markdown в папке: {PROCESSED_BOOKMARKS_DIR}")

    if not os.path.exists(PROCESSED_BOOKMARKS_DIR):
        logger.warning(f"Папка '{PROCESSED_BOOKMARKS_DIR}' не найдена. Возможно, bookmarks еще не были обработаны.")
        return

    # Получаем список всех подпапок (предполагаем, что они названы по ID закладки)
    all_bookmark_dirs = sorted([d for d in os.listdir(PROCESSED_BOOKMARKS_DIR) if os.path.isdir(os.path.join(PROCESSED_BOOKMARKS_DIR, d))])

    if not all_bookmark_dirs:
        logger.info(f"В папке '{PROCESSED_BOOKMARKS_DIR}' не найдено обработанных закладок.")
        return
    
    bookmarks_to_convert = []
    for bookmark_dir in all_bookmark_dirs:
        html_file_path = os.path.join(PROCESSED_BOOKMARKS_DIR, bookmark_dir, "index.html")
        if os.path.isfile(html_file_path) and os.path.getsize(html_file_path) > 0:
            bookmarks_to_convert.append(bookmark_dir)
            if len(bookmarks_to_convert) >= CONVERT_LIMIT_VALID:
                break
    
    if not bookmarks_to_convert:
        logger.info(f"В папке '{PROCESSED_BOOKMARKS_DIR}' не найдено валидных закладок для конвертации (файл index.html отсутствует или пуст).")
        return

    logger.info(f"Будут конвертированы первые {len(bookmarks_to_convert)} валидных закладок.")

    for bookmark_id in bookmarks_to_convert:
        bookmark_folder = os.path.join(PROCESSED_BOOKMARKS_DIR, bookmark_id)
        html_file_path = os.path.join(bookmark_folder, "index.html")
        md_file_path = os.path.join(bookmark_folder, "content.md")

        if not os.path.isfile(html_file_path) or os.path.getsize(html_file_path) == 0:
            logger.warning(f"Файл '{html_file_path}' не существует или пуст, пропуск конвертации для ID {bookmark_id}.")
            continue
        try:
            with open(html_file_path, "r", encoding="utf-8") as f:
                html_content = f.read()

            # Конвертация HTML в Markdown с помощью markdownify
            markdown_content = md(html_content)

            with open(md_file_path, "w", encoding="utf-8") as f:
                f.write(markdown_content)
            logger.success(f"Успешно сконвертирован '{html_file_path}' в '{md_file_path}'.")

        except Exception as e:
            logger.error(f"Ошибка при конвертации '{html_file_path}' для ID {bookmark_id}: {e}")

    logger.info("Конвертация HTML в Markdown завершена.")

if __name__ == "__main__":
    asyncio.run(convert_html_to_md())