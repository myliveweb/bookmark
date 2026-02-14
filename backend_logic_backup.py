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

import json # Добавляем для парсинга JSON
import re # Добавляем для извлечения данных из текста, если JSON невалидный
from llm.model import get_llm_completion, active_llm_provider # Изменяем импорт, добавляем active_llm_provider
from models import AIAnalysisResult
import httpx # Добавляем для типизации исключений, если понадобится

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
    if not active_llm_provider: 
        raise Exception("ИИ-двигатель не инициализирован или не активен")
    
    # Ограничиваем текст до 10000 символов, чтобы влезть в лимит Groq (TPM safety)
    # Это значение может быть скорректировано в зависимости от провайдера и модели
    truncated_content = markdown_content[:10000]
    
    prompt = f"""Ты — эксперт по анализу IT-контента. Проанализируй текст и выдели 1-3 IT-категории и краткое резюме (2-3 предложения) на русском языке.
Текст: {truncated_content}"""
    
    try:
        # get_llm_completion возвращает dict, поэтому нужно будет его распарсить в AIAnalysisResult
        llm_response_dict = await get_llm_completion(prompt)
        
        # Предполагаем, что ответ от LLM будет в формате, который можно преобразовать в AIAnalysisResult.
        # Это может быть либо уже готовый JSON, либо текст, который нужно распарсить.
        # Для Groq/OpenRouter это будет в `choices[0].message.content`, для Ollama - в `response`
        
        content_str = ""
        if "choices" in llm_response_dict and len(llm_response_dict["choices"]) > 0:
            content_str = llm_response_dict["choices"][0]["message"]["content"]
        elif "response" in llm_response_dict:
            # Ollama response for /api/generate usually has "response" key
            content_str = llm_response_dict["response"] 
        else:
            raise ValueError(f"Неожиданный формат ответа от LLM: {llm_response_dict}")

        # Попытка распарсить строку в JSON и затем в AIAnalysisResult
        try:
            parsed_content = json.loads(content_str)
            result = AIAnalysisResult(**parsed_content)
        except (json.JSONDecodeError, TypeError, ValueError) as json_error:
            logger.warning(f"Не удалось распарсить ответ LLM в JSON, пробуем извлечь текст напрямую: {json_error}. Контент: {content_str[:200]}...")
            # Если не JSON, пытаемся извлечь summary и categories из текста, или ставим заглушку
            summary_match = re.search(r"Резюме:\s*(.*?)(?:\n|$)", content_str, re.DOTALL)
            categories_match = re.search(r"Категории:\s*(.*?)(?:\n|$)", content_str)
            
            summary_text = summary_match.group(1).strip() if summary_match else content_str[:200] + "..." # Берем начало текста
            categories_text = categories_match.group(1).strip() if categories_match else "Разное"
            result = AIAnalysisResult(summary=summary_text, categories=[c.strip() for c in categories_text.split(',') if c.strip()])

        categories = result.categories if result.categories else ["Разное"]
        return {"summary": result.summary, "categories": categories}
    except Exception as e:
        logger.error(f"AI Error: {e}")
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

async def regenerate_new_summary(summary: str, history: str, project_path: str):
    try:
        # if not active_llm_provider:
        #     raise Exception("ИИ-двигатель не инициализирован или не активен для генерации резюме.")

        prompt = f"""
# ROLE: Senior Systems Architect & Context Manager

# TASK
Update the "Continuous Project Summary" by integrating new conversation history with the existing summary. 

# INPUT DATA
[CURRENT PROJECT ROOT]
{project_path}

[EXISTING SUMMARY]
{summary}

[NEW MESSAGES]
{history}

# CORE OBJECTIVE
Preserve the EXACT technical state of the project. Your goal is INCREMENTAL GROWTH: keep 100% of valid old technical info and add new facts.

# STRICT RULES (CRITICAL)
1. **No Path Hallucinations**: Use ONLY the actual file paths. If a file is in the root, write `./filename.py`. DO NOT create folders like `backend/` or `frontend/` if they are not in the [CURRENT PROJECT ROOT] or mentioned as such.
2. **Technical Integrity**: Never delete file paths, database schemas, or logic descriptions from the [EXISTING SUMMARY] unless the [NEW MESSAGES] explicitly state they were removed.
3. **Data Flows**: Keep all API endpoints and data processing logic (e.g., "how the conveyor works").
4. **Output Length**: Do not truncate. If the project grows, the summary MUST grow.

# INSTRUCTION FOR INCREMENTAL UPDATE
- **Merge Logic**: Read [EXISTING SUMMARY] first. Identify what is new in [NEW MESSAGES]. Add new files to "Architecture", new endpoints to "Database & API", and new achievements to "Recent Progress".
- **Refinement**: Only update existing lines if the technology or path has actually changed.
- **Language**: Summary in Russian. Technical terms, file paths, and code entities in English.

# OUTPUT FORMAT (Keep these exact headers)
## PROJECT STATE & SUMMARY

### 1. Technical Stack
(Keep old, add new)

### 2. Architecture & Files
(USE ACTUAL PATHS ONLY. Format: `./file.py` or `path/to/file.ts`)

### 3. Database & API
(List all active endpoints and schemas)

### 4. Recent Progress & Decisions
(Focus on what was done in the [NEW MESSAGES])

### 5. Current Focus & Blocking Issues
(What is the immediate next step?)
"""
        llm_response_dict = await get_llm_completion(prompt)
        
        new_summary_content = ""
        if "choices" in llm_response_dict and len(llm_response_dict["choices"]) > 0:
            new_summary_content = llm_response_dict["choices"][0]["message"]["content"]
        elif "response" in llm_response_dict:
            new_summary_content = llm_response_dict["response"]
        else:
            raise ValueError(f"Неожиданный формат ответа от LLM для регенерации резюме: {llm_response_dict}")

        return new_summary_content.strip()
    except Exception as e:
        logger.error(f"Regenerate summary Error: {e}")
        raise Exception(f"Regenerate summary Error: {e}")
