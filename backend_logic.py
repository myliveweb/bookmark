import os
import asyncio
import uuid
import time
from urllib.parse import urlparse
from playwright.async_api import async_playwright
from loguru import logger
from markitdown import MarkItDown
from bs4 import BeautifulSoup
from supabase import create_client, Client
from dotenv import load_dotenv

from llm.model import get_llm_engine
from langchain_core.messages import HumanMessage
from models import AIAnalysisResult

# Загрузка окружения
load_dotenv()

# Константы
TARGET_WIDTH = 1280
TARGET_HEIGHT = 720
TEMP_DIR = "temp_screenshots"
os.makedirs(TEMP_DIR, exist_ok=True)

PROXY_URL = os.getenv("PROXY_URL")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# --- ПАПКИ ДЛЯ ИМПОРТА ---
TARGET_FOLDERS = ["Разработка", "Полезное"]

# --- АВАРИЙНЫЙ ВЫХОД ЕСЛИ НЕТ ПРОКСИ ---
if not PROXY_URL or "http" not in PROXY_URL:
    logger.critical("CRITICAL: PROXY_URL is missing or invalid! Emergency shutdown.")
    raise SystemExit("Error: PROXY_URL is mandatory for this project.")

# Инициализация клиентов
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
llm_engine = get_llm_engine()
md_converter = MarkItDown()

def parse_chrome_bookmarks(html_content: str):
    """Парсит HTML-файл закладок Chrome и возвращает список ссылок из нужных папок."""
    soup = BeautifulSoup(html_content, 'html.parser')
    extracted_data = {}
    all_folders = soup.find_all('h3')
    
    for h3 in all_folders:
        folder_name = h3.get_text().strip()
        if folder_name in TARGET_FOLDERS:
            parent_dl = h3.find_next('dl')
            if parent_dl:
                links = parent_dl.find_all('a')
                for a in links:
                    url = a.get('href')
                    if not url or url.startswith('chrome://') or url.startswith('about:'):
                        continue
                    
                    title = a.get_text().strip()
                    try:
                        add_date = int(a.get('add_date', 0))
                    except:
                        add_date = 0
                    
                    # Сохраняем самую свежую версию ссылки, если она дублируется
                    if url in extracted_data:
                        if add_date > extracted_data[url]['add_date']:
                            extracted_data[url] = {"title": title, "add_date": add_date}
                    else:
                        extracted_data[url] = {"title": title, "add_date": add_date}

    return [{"url": url, "title": info["title"], "add_date": info["add_date"]} for url, info in extracted_data.items()]

async def take_screenshot(url: str, output_path: str):
    """Делает скриншот через Playwright с ОБЯЗАТЕЛЬНЫМ прокси."""
    async with async_playwright() as p:
        parsed_proxy = urlparse(PROXY_URL)
        proxy_config = {
            "server": f"{parsed_proxy.scheme}://{parsed_proxy.hostname}:{parsed_proxy.port}",
            "username": parsed_proxy.username,
            "password": parsed_proxy.password
        }
        
        browser = await p.chromium.launch(proxy=proxy_config)
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            proxy=proxy_config
        )
        page = await context.new_page()
        
        try:
            # Ограничиваем таймаут и ждем загрузки
            response = await page.goto(str(url), timeout=30000, wait_until="load")
            
            if not response or response.status >= 400:
                raise Exception(f"Page returned status {response.status if response else 'None'}")
                
            title = await page.title()
            html = await page.content()
            
            if len(html) < 200:
                raise Exception("Page content is too short")
                
            await page.screenshot(path=output_path, full_page=False) # Не full_page для красоты превью
            return title, html
        finally:
            await browser.close()

async def process_image(input_path: str, output_path: str):
    """Обрезка и ресайз через FFmpeg."""
    command = [
        "ffmpeg", "-i", input_path,
        "-vf", f"scale={TARGET_WIDTH}:{TARGET_HEIGHT}:force_original_aspect_ratio=increase,crop={TARGET_WIDTH}:{TARGET_HEIGHT}:(in_w-{TARGET_WIDTH})/2:0",
        "-y", output_path
    ]
    process = await asyncio.create_subprocess_exec(
        *command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    await process.communicate()

def upload_to_supabase(file_path: str, storage_path: str, content_type: str):
    """Загрузка в Supabase Storage."""
    with open(file_path, "rb") as f:
        supabase.storage.from_("screenshots").upload(
            path=storage_path, file=f,
            file_options={"content-type": content_type, "upsert": "true"}
        )

async def analyze_markdown_content(markdown_content: str):
    """ИИ-анализ контента."""
    if not llm_engine: 
        raise Exception("ИИ-двигатель не инициализирован")
    
    # Ограничиваем текст до 10000 символов, чтобы влезть в лимит Groq (TPM safety)
    truncated_content = markdown_content[:10000]
    
    prompt = f"""Ты — эксперт по анализу IT-контента. Проанализируй текст и выдели 1-3 IT-категории и краткое резюме (2-3 предложения) на русском языке.
Текст: {truncated_content}"""
    
    try:
        result: AIAnalysisResult = await llm_engine.send_message_structured_outputs(prompt, AIAnalysisResult)
        # Если категории пустые, мы всё равно считаем это успехом AI (бывают пустые страницы), 
        # но воркер может зациклиться. Поэтому принудительно ставим заглушку 'Разное' если совсем пусто.
        categories = result.categories if result.categories else ["Разное"]
        return {"summary": result.summary, "categories": categories}
    except Exception as e:
        logger.error(f"AI Error: {e}")
        # НЕ возвращаем заглушку, а пробрасываем ошибку выше, чтобы цикл зафиксировал её в БД
        raise e

async def process_bookmark_full_cycle(bookmark_id: int, url: str):
    """
    ПОЛНЫЙ ЦИКЛ ОБРАБОТКИ ЗАКЛАДКИ.
    Используется и сервером (main.py) и воркером (conveyor_worker.py).
    """
    unique_id = uuid.uuid4().hex
    raw_path = os.path.join(TEMP_DIR, f"{unique_id}_raw.png")
    proc_path = os.path.join(TEMP_DIR, f"{unique_id}.png")
    html_path = os.path.join(TEMP_DIR, f"{unique_id}.html")
    
    start_all = time.perf_counter()
    logger.info(f"--- Начало цикла для закладки #{bookmark_id} ({url}) ---")

    try:
        # 1. Скрапинг и Скриншот
        logger.info(f"[1/5] Скрапинг страницы...")
        title, html_content = await take_screenshot(url, raw_path)
        
        with open(html_path, "w", encoding="utf-8") as f: 
            f.write(html_content)
        
        # 2. Обработка изображения
        logger.info(f"[2/5] Обработка скриншота...")
        await process_image(raw_path, proc_path)
        
        # 3. Конвертация в Markdown и ИИ Анализ
        logger.info(f"[3/5] Конвертация и ИИ Анализ (Groq)...")
        res = md_converter.convert(html_path)
        ai_data = await analyze_markdown_content(res.text_content)
        
        # 4. Загрузка в Storage
        logger.info(f"[4/5] Загрузка assets в Supabase...")
        storage_filename = f"{bookmark_id}.png"
        upload_to_supabase(proc_path, storage_filename, "image/png")
        image_url = supabase.storage.from_("screenshots").get_public_url(storage_filename)
        
        # 5. Обновление БД
        logger.info(f"[5/5] Обновление записи в БД...")
        update_data = {
            "title": title,
            "summary": ai_data["summary"],
            "categories": ai_data["categories"],
            "is_processed": True,
            "processing_error": None
        }
        supabase.table("bookmarks").update(update_data).eq("id", bookmark_id).execute()
        
        duration = time.perf_counter() - start_all
        logger.success(f"--- Закладка #{bookmark_id} обработана успешно за {duration:.2f} сек. ---")
        return update_data

    except Exception as e:
        logger.error(f"Ошибка цикла для закладки #{bookmark_id}: {str(e)}")
        # Записываем ошибку в БД и помечаем как обработанную, чтобы воркер не зацикливался
        supabase.table("bookmarks").update({
            "processing_error": str(e),
            "is_processed": True  # Помечаем True, чтобы воркер пропустил её в следующий раз
        }).eq("id", bookmark_id).execute()
        raise e
    finally:
        # Очистка временных файлов
        for p in [raw_path, proc_path, html_path]:
            if os.path.exists(p): os.remove(p)
