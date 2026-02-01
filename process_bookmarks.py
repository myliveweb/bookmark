# process_bookmarks.py
import asyncio
import os
import time
from dotenv import load_dotenv
from supabase import create_client, AsyncClient
from loguru import logger
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
from urllib.parse import urlparse # Импортируем urlparse

# Загрузка переменных окружения
load_dotenv()

# Настройка клиента Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
PROXY_URL = os.getenv("PROXY_URL") # Загружаем PROXY_URL

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Supabase credentials not found in .env file")

supabase: AsyncClient = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- Основные настройки ---
BOOKMARKS_PER_RUN = 1000000 # Очень большое число, чтобы обработать все за раз
PAGE_TIMEOUT = 30000  # 30 секунд
OUTPUT_DIR = "processed_bookmarks"

async def process_single_bookmark(page, bookmark):
    """Обрабатывает одну закладку: сохраняет HTML и делает скриншот."""
    bookmark_id = bookmark['id']
    url = bookmark['url']
    logger.info(f"Обработка закладки ID: {bookmark_id}, URL: {url}")

    bookmark_folder = os.path.join(OUTPUT_DIR, str(bookmark_id))
    # os.makedirs(bookmark_folder, exist_ok=True) # Перемещено

    html_path = os.path.join(bookmark_folder, "index.html")
    screenshot_path = os.path.join(bookmark_folder, "screenshot.png")

    try:
        # Переходим по URL с таймаутом
        response = await page.goto(url, timeout=PAGE_TIMEOUT)
        
        # Ждем, пока не будет сетевой активности
        await page.wait_for_load_state('networkidle')
        
        # Проверяем статус ответа
        if response and not response.ok:
            raise Exception(f"HTTP status code: {response.status}")

        # --- Создаем папку только после успешной загрузки ---
        os.makedirs(bookmark_folder, exist_ok=True)

        # Сохраняем HTML
        content = await page.content()
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(content)

        # Делаем скриншот
        await page.screenshot(path=screenshot_path, full_page=True)

        # Обновляем статус в Supabase
        update_query = supabase.table("bookmarks").update({"is_processed": True, "processing_error": None}).eq("id", bookmark_id)
        await asyncio.get_event_loop().run_in_executor(None, update_query.execute)
        logger.success(f"Успешно обработана закладка ID: {bookmark_id}")

    except PlaywrightTimeoutError:
        error_message = f"Таймаут {PAGE_TIMEOUT / 1000}с при загрузке страницы."
        logger.warning(f"Ошибка для ID {bookmark_id}: {error_message}")
        update_query = supabase.table("bookmarks").update({"is_processed": False, "processing_error": error_message}).eq("id", bookmark_id)
        await asyncio.get_event_loop().run_in_executor(None, update_query.execute)
    
    except Exception as e:
        error_message = f"Непредвиденная ошибка: {str(e)}"
        logger.error(f"Ошибка для ID {bookmark_id}: {error_message}")
        update_query = supabase.table("bookmarks").update({"is_processed": False, "processing_error": error_message}).eq("id", bookmark_id)
        await asyncio.get_event_loop().run_in_executor(None, update_query.execute)


async def main():
    start_time = time.time()
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    logger.info("Запрос необработанных закладок из Supabase...")
    
    # Получаем закладки, которые еще не обработаны и начинаются с https
    query = (
        supabase.table("bookmarks")
        .select("id, url")
        .eq("is_processed", False)
        .like("url", "https://%")
        .order("id")
        .limit(BOOKMARKS_PER_RUN)
    )
    response = await asyncio.get_event_loop().run_in_executor(None, query.execute)

    if not response.data:
        logger.info("Нет новых закладок для обработки.")
        return

    bookmarks = response.data
    logger.info(f"Найдено {len(bookmarks)} закладок для обработки.")

    async with async_playwright() as p:
        launch_options = {}
        if PROXY_URL:
            parsed_proxy = urlparse(PROXY_URL)
            proxy_config = {"server": f"{parsed_proxy.scheme}://{parsed_proxy.hostname}:{parsed_proxy.port}"}
            if parsed_proxy.username:
                proxy_config["username"] = parsed_proxy.username
            if parsed_proxy.password:
                proxy_config["password"] = parsed_proxy.password
            launch_options["proxy"] = proxy_config
            logger.info(f"Запуск браузера с прокси: {proxy_config['server']}")
        else:
            logger.info("Запуск браузера без прокси.")
            
        browser = await p.chromium.launch(**launch_options)

        for bookmark in bookmarks:
            page = await browser.new_page() # Создаем новую страницу для каждой закладки
            await process_single_bookmark(page, bookmark)
            await page.close() # Закрываем страницу после использования

        await browser.close()

    logger.success(f"Работа завершена. Общее время: {time.time() - start_time:.2f} сек.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nПрограмма прервана пользователем (Ctrl+C)")
    except Exception as e:
        logger.exception("Произошла глобальная ошибка в работе программы:")
