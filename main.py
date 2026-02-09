import os
import asyncio
import subprocess
import time
import uuid
import json
from typing import List
from urllib.parse import urlparse

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from supabase import create_client, Client
from playwright.async_api import async_playwright
from loguru import logger
from slugify import slugify
from markitdown import MarkItDown
from datetime import datetime, timedelta

from llm.model import ModelOllama
from langchain_core.messages import HumanMessage
from models import (
    Bookmark, BookmarkCreate, ResnapRequest, CommitScreenshotRequest, 
    CategoriesResponse, CreateCategoryRequest, ProcessUrlRequest, 
    FinalizeBookmarkRequest, ProcessUrlResponse, AIAnalysisResult, 
    RegenerateSummaryRequest

)

# Выгружаем переменные окружения
load_dotenv()

# Инициализация FastAPI
app = FastAPI(title="Bookmark Manager")

# Инициализация продвинутого ИИ-движка
try:
    llm_engine = ModelOllama(provider="gemini")
except Exception as e:
    logger.error(f"Failed to initialize LLM engine: {e}")
    llm_engine = None

md_converter = MarkItDown()

# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключение к Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
PROXY_URL = os.getenv("PROXY_URL")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Supabase credentials not found in .env file")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Constants
TARGET_WIDTH = 1280
TARGET_HEIGHT = 720
TEMP_DIR = "temp_screenshots"

os.makedirs(TEMP_DIR, exist_ok=True)

# --- Helpers ---

async def analyze_markdown_content(markdown_content: str):
    """Анализирует текст через продвинутый движок ModelOllama."""
    if not llm_engine:
        return {"summary": "", "categories": []}

    prompt = f"""Ты — эксперт по классификации и суммаризации контента.
Проанализируй следующий текст и выполни две задачи:

1. **Categories (categories):** Определи наиболее релевантные категории для текста. Выбирай категории СТРОГО И ТОЛЬКО из следующего списка:
- **Программирование и Разработка:** Python, JavaScript, TypeScript, PHP, Go, Java, C#, C++, Ruby, Rust, Swift, Kotlin, Bash/Shell, Node.js, Django, Flask, FastAPI, Laravel, Spring, ASP.NET, Ruby on Rails, Express.js, NestJS, .NET, React, Vue.js, Angular, Svelte, jQuery, Next.js, Nuxt.js, Web Components, Android, iOS, React Native, Flutter, Electron, WPF, Qt, Unity, Unreal Engine, Godot, Game Development, Embedded Systems, IoT, C/C++ (Low-Level), Assembler, 1С-Битрикс/Bitrix Framework
- **Инфраструктура и DevOps:** AWS, Google Cloud (GCP), Microsoft Azure, Yandex.Cloud, DigitalOcean, Heroku, Docker, Kubernetes, OpenShift, Podman, Helm, Jenkins, GitLab CI, GitHub Actions, CircleCI, Travis CI, Argo CD, Ansible, Terraform, Puppet, Chef, SaltStack, Prometheus, Grafana, ELK Stack, Sentry, Datadog, VMware, VirtualBox, KVM, Xen, Linux, Windows Server, macOS, Unix, Сетевое администрирование, Протоколы, Firewall
- **Базы Данных:** PostgreSQL, MySQL, MariaDB, SQL Server, Oracle, SQLite, MongoDB, Redis, Cassandra, Neo4j, Couchbase, Elasticsearch (DB), Data Warehousing, Data Lake, Snowflake, BigQuery, GraphQL (DB), REST API Design
- **Искусственный Интеллект и Машинное Обучение:** TensorFlow, PyTorch, Scikit-learn, Keras, Data Science, MLOps, Нейронные сети, Computer Vision, NLP, LLMs, Diffusion Models, GANs, Алгоритмы ML, Этика ИИ, Теория ML
- **Безопасность (Cybersecurity):** OWASP, XSS, SQL Injection, CSRF, Пентестинг, IDS/IPS, VPN, OAuth, OpenID Connect, JWT, SSO, Криптография, Шифрование, Хеширование, TLS/SSL, Threat Modeling, Security Best Practices
- **Дизайн и UX/UI:** UX Дизайн, UI Дизайн, Figma, Sketch, Adobe XD, Прототипирование, Веб-дизайн, Адаптивный дизайн, CSS Frameworks (Tailwind CSS, Bootstrap), Webflow, Графический Дизайн, Типографика, Иконография, Брендинг
- **Менеджмент и Бизнес в IT:** NotebookLM, Agile, Scrum, Kanban, Waterfall, Jira, Trello, Product Management, Стратегия продукта, MVP, Бизнес-анализ, Аналитика, Метрики, KPI, Карьера в IT, Собеседования, Резюме, Развитие карьеры, Soft Skills, Стартапы, Инвестиции, Бизнес-модели
- **Общие IT-Темы:** Новости IT, Тренды в IT, Технические Блоги, Статьи (IT), Обзоры (IT), Конференции/Мероприятия (IT), Образование/Курсы (IT), Open Source, Книги/Ресурсы (IT), Другое (IT)

Постарайся выбрать 1-3 наиболее релевантные категории. Если ничего не подходит - "Другое (IT)".

2. **Summary (summary):** Создай краткое, информативное резюме текста (2-3 предложения) на РУССКОМ языке.

Текст для анализа:
---
{markdown_content[:50000]}
---
"""
    try:
        # Теперь это асинхронный вызов!
        result: AIAnalysisResult = await llm_engine.send_message_structured_outputs(prompt, AIAnalysisResult)
        return {
            "summary": result.summary,
            "categories": result.categories
        }
    except Exception as e:
        logger.error(f"Advanced LLM Analysis error: {e}")
        return {"summary": "", "categories": []}

async def take_screenshot(url: str, output_path: str):
    """Takes a screenshot using Playwright."""
    async with async_playwright() as p:
        launch_options = {}
        if PROXY_URL:
            parsed_proxy = urlparse(PROXY_URL)
            proxy_config = {"server": f"{parsed_proxy.scheme}://{parsed_proxy.hostname}:{parsed_proxy.port}"}
            if parsed_proxy.username: proxy_config["username"] = parsed_proxy.username
            if parsed_proxy.password: proxy_config["password"] = parsed_proxy.password
            launch_options["proxy"] = proxy_config
        
        browser = await p.chromium.launch(**launch_options)
        context = await browser.new_context(viewport={"width": 1920, "height": 1080})
        page = await context.new_page()
        
        try:
            await page.goto(str(url), timeout=30000)
            await page.wait_for_load_state("networkidle", timeout=30000)
        except Exception as e:
            logger.warning(f"Page load warning: {e}")
        
        await page.screenshot(path=output_path, full_page=True)
        await browser.close()

async def process_image(input_path: str, output_path: str):
    """Resizes and crops the image using FFmpeg."""
    command = [
        "ffmpeg",
        "-i", input_path,
        "-vf", f"scale={TARGET_WIDTH}:{TARGET_HEIGHT}:force_original_aspect_ratio=increase,crop={TARGET_WIDTH}:{TARGET_HEIGHT}:(in_w-{TARGET_WIDTH})/2:0",
        "-y",
        output_path
    ]
    
    process = await asyncio.create_subprocess_exec(
        *command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await process.communicate()
    
    if process.returncode != 0:
        logger.error(f"FFmpeg error: {stderr.decode()}")
        raise RuntimeError("FFmpeg processing failed")

def upload_to_supabase(file_path: str, storage_path: str, content_type: str = "image/png"):
    """Uploads file to Supabase Storage."""
    with open(file_path, "rb") as f:
        supabase.storage.from_("screenshots").upload(
            path=storage_path,
            file=f,
            file_options={"content-type": content_type, "upsert": "true"}
        )

async def regenerate_new_summary(summary_old_text, summary_new):
    # --- Формирование промпта ---
    prompt_template = """
# ROLE: Senior Systems Architect & Context Manager

# TASK
Update the "Continuous Project Summary" by integrating new conversation history with the existing summary. 

# INPUT DATA
Below is the existing summary and the new messages to be integrated.

[EXISTING SUMMARY]
{summary_old_text}

[NEW MESSAGES]
{summary_new}

# CORE OBJECTIVE
Preserve the technical state of the project so that an AI Agent can resume work without losing track of files, logic, or decisions.

# STRICT RULES FOR CONTENT PRESERVATION
1. **Tech Stack & Environment**: Always keep the list of languages, frameworks (Python, FastAPI, Nuxt), and server statuses.
2. **File & Structure Map**: Never delete file paths (e.g., `frontend/nuxt-app/app/components/BookmarkCard.vue`) or database schemas.
3. **States & Constants**: If a variable, port, or API endpoint was decided upon, it must remain in the summary.
4. **Logic & Workflow**: Document "How it works" for complex features (e.g., "Finalization moves files from /tmp to /storage via ID").
5. **Pending Tasks**: Maintain a "Todo" or "Current Focus" list at the end of the summary.

# INSTRUCTION FOR INCREMENTAL UPDATE
- **Merge, don't just append**: If new info updates old info (e.g., "Moved from File to Postgres"), update the corresponding section.
- **Compress Narrative**: Remove greetings, politeness, and minor debugging steps. Keep only the "Final Result" of a discussion.
- **Language**: Maintain the summary in Russian, but keep technical terms, file paths, and code entities in their original English form.

# OUTPUT FORMAT (Strictly follow this structure)
## PROJECT STATE & SUMMARY

### 1. Technical Stack
(List of technologies and versions)

### 2. Architecture & Files
(File paths and their current roles)

### 3. Database & API
(Schemas, endpoints, and data flows)

### 4. Recent Progress & Decisions
(What was achieved in the last 50 messages)

### 5. Current Focus & Blocking Issues
(What are we doing right now?)
"""
    prompt = prompt_template.format(summary_old_text=summary_old_text, summary_new=summary_new)
    response = await llm_engine.llm.ainvoke([HumanMessage(content=prompt)])

    return response.content.strip()

# --- API Endpoints ---

@app.get("/")
def read_root():
    return {"status": "ok"}

@app.get("/bookmarks", response_model=List[Bookmark])
def get_bookmarks():
    response = supabase.table('bookmarks').select('*').order('id', desc=True).execute()
    if response.data is None:
        raise HTTPException(status_code=500, detail="Could not fetch bookmarks")
    return response.data

@app.post("/bookmarks", response_model=Bookmark, status_code=201)
def create_bookmark(bookmark: BookmarkCreate):
    bookmark_dict = bookmark.model_dump(mode='json')
    response = supabase.table('bookmarks').insert(bookmark_dict).execute()
    if not response.data:
         raise HTTPException(status_code=500, detail="Could not create bookmark")
    return response.data[0]

@app.post("/api/resnap")
async def resnap_bookmark(request: ResnapRequest):
    unique_id = uuid.uuid4().hex
    raw_screenshot_path = os.path.join(TEMP_DIR, f"{unique_id}_raw.png")
    processed_screenshot_path = os.path.join(TEMP_DIR, f"{unique_id}.png")
    try:
        await take_screenshot(request.url, raw_screenshot_path)
        await process_image(raw_screenshot_path, processed_screenshot_path)
        temp_storage_path = f"temp/{unique_id}.png"
        upload_to_supabase(processed_screenshot_path, temp_storage_path)
        public_url = supabase.storage.from_("screenshots").get_public_url(temp_storage_path)
        return {"temp_url": public_url, "temp_filename": temp_storage_path}
    except Exception as e:
        logger.error(f"Resnap error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if os.path.exists(raw_screenshot_path): os.remove(raw_screenshot_path)
        if os.path.exists(processed_screenshot_path): os.remove(processed_screenshot_path)

@app.post("/api/commit-screenshot")
def commit_screenshot(request: CommitScreenshotRequest):
    final_path = f"image/{request.bookmark_id}.png"
    try:
        supabase.storage.from_("screenshots").move(request.temp_filename, final_path)
        return {"status": "success", "final_path": final_path}
    except Exception as e:
        logger.error(f"Commit error: {e}")
        try:
            temp_data = supabase.storage.from_("screenshots").download(request.temp_filename)
            supabase.storage.from_("screenshots").upload(final_path, temp_data, {"content-type": "image/png", "upsert": "true"})
            supabase.storage.from_("screenshots").remove([request.temp_filename])
            return {"status": "success", "method": "fallback_copy"}
        except Exception as e2:
            raise HTTPException(status_code=500, detail=f"Could not commit: {e2}")

@app.post("/api/categories", status_code=201)
def create_category(request: CreateCategoryRequest):
    parent_to_assign = "Общие IT-Темы"
    if request.context_slug:
        try:
            response = supabase.table("categories").select("parent_category").eq("slug", request.context_slug).single().execute()
            if response.data and response.data.get("parent_category"):
                parent_to_assign = response.data["parent_category"]
        except: pass
    new_slug = slugify(request.name, replacements=[['+', '-plus-'], ['/', '-or-']])
    new_data = {"name": request.name, "slug": new_slug, "parent_category": parent_to_assign, "bookmarks_count": 0}
    try:
        response = supabase.table("categories").upsert(new_data, on_conflict="name").execute()
        return response.data[0]
    except Exception as e:
        find = supabase.table('categories').select('*').eq('name', request.name).single().execute()
        if find.data: return find.data
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/categories", response_model=CategoriesResponse)
def get_categories():
    response = supabase.table("categories").select("name").order("name", desc=False).execute()
    return {"categories": [row["name"] for row in response.data] if response.data else []}

@app.post("/api/process-url", response_model=ProcessUrlResponse)
async def process_url(request: ProcessUrlRequest):
    unique_id = uuid.uuid4().hex
    raw_screenshot_path = os.path.join(TEMP_DIR, f"{unique_id}_raw.png")
    processed_screenshot_path = os.path.join(TEMP_DIR, f"{unique_id}.png")
    temp_html_path = os.path.join(TEMP_DIR, f"{unique_id}.html")
    temp_md_path = os.path.join(TEMP_DIR, f"{unique_id}.md")
    
    try:
        page_title = ""
        markdown_text = ""
        
        # 1. Playwright
        async with async_playwright() as p:
            launch_options = {}
            if PROXY_URL:
                parsed_proxy = urlparse(PROXY_URL)
                proxy_config = {"server": f"{parsed_proxy.scheme}://{parsed_proxy.hostname}:{parsed_proxy.port}"}
                if parsed_proxy.username: proxy_config["username"] = parsed_proxy.username
                if parsed_proxy.password: proxy_config["password"] = parsed_proxy.password
                launch_options["proxy"] = proxy_config
            
            browser = await p.chromium.launch(**launch_options)
            context = await browser.new_context(viewport={"width": 1920, "height": 1080})
            page = await context.new_page()
            
            try:
                await page.goto(str(request.url), timeout=30000)
                await page.wait_for_load_state("networkidle", timeout=30000)
                page_title = await page.title()
                html_content = await page.content()
                with open(temp_html_path, "w", encoding="utf-8") as f: f.write(html_content)
                await page.screenshot(path=raw_screenshot_path, full_page=True)
            except Exception as e:
                logger.warning(f"Page load warning: {e}")
                if not page_title: page_title = str(request.url)
            finally:
                await browser.close()

        # 2. FFmpeg
        if os.path.exists(raw_screenshot_path):
            await process_image(raw_screenshot_path, processed_screenshot_path)
            
        # 3. MarkItDown
        if os.path.exists(temp_html_path):
            try:
                result = md_converter.convert(temp_html_path)
                markdown_text = result.text_content
                with open(temp_md_path, "w", encoding="utf-8") as f: f.write(markdown_text)
            except Exception as md_err:
                logger.error(f"MarkItDown conversion error: {md_err}")

        # 4. Продвинутый Анализ ИИ (теперь асинхронный!)
        ai_data = {"summary": "", "categories": []}
        if markdown_text:
            ai_data = await analyze_markdown_content(markdown_text)
        
        # 5. Upload to Supabase
        screenshot_storage_path = f"temp/{unique_id}.png"
        if os.path.exists(processed_screenshot_path):
            upload_to_supabase(processed_screenshot_path, screenshot_storage_path, "image/png")
            
        html_storage_path = f"temp/{unique_id}.html"
        if os.path.exists(temp_html_path):
            upload_to_supabase(temp_html_path, html_storage_path, "text/html")
                
        md_storage_path = f"temp/{unique_id}.md"
        if os.path.exists(temp_md_path):
            upload_to_supabase(temp_md_path, md_storage_path, "text/markdown")

        public_url = supabase.storage.from_("screenshots").get_public_url(screenshot_storage_path)
        
        return {
            "status": "success", "message": "URL processed with advanced AI analysis",
            "suggested_title": page_title, "temp_url": public_url,
            "temp_screenshot_path": screenshot_storage_path, "temp_html_path": html_storage_path,
            "temp_markdown_path": md_storage_path, "uuid": unique_id,
            "suggested_summary": ai_data["summary"], "suggested_categories": ai_data["categories"]
        }
    except Exception as e:
        logger.error(f"Processing error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Исправлено: используем правильное имя переменной processed_screenshot_path
        for f in [raw_screenshot_path, processed_screenshot_path, temp_html_path, temp_md_path]:
            if os.path.exists(f): os.remove(f)

@app.post("/api/finalize-bookmark")
def finalize_bookmark(request: FinalizeBookmarkRequest):
    final_screenshot_path = f"image/{request.bookmark_id}.png"
    final_html_path = f"html/{request.bookmark_id}.html"
    final_md_path = f"markdown/{request.bookmark_id}.md"
    results = {"screenshot": "skipped", "html": "skipped", "markdown": "skipped"}
    try:
        if request.temp_screenshot_path:
            try:
                supabase.storage.from_("screenshots").move(request.temp_screenshot_path, final_screenshot_path)
                results["screenshot"] = "moved"
            except:
                data = supabase.storage.from_("screenshots").download(request.temp_screenshot_path)
                supabase.storage.from_("screenshots").upload(final_screenshot_path, data, {"content-type": "image/png", "upsert": "true"})
                supabase.storage.from_("screenshots").remove([request.temp_screenshot_path])
                results["screenshot"] = "copied"
        if request.temp_html_path:
            try:
                supabase.storage.from_("screenshots").move(request.temp_html_path, final_html_path)
                results["html"] = "moved"
            except:
                data = supabase.storage.from_("screenshots").download(request.temp_html_path)
                supabase.storage.from_("screenshots").upload(final_html_path, data, {"content-type": "text/html", "upsert": "true"})
                supabase.storage.from_("screenshots").remove([request.temp_html_path])
                results["html"] = "copied"
        if request.temp_markdown_path:
            try:
                supabase.storage.from_("screenshots").move(request.temp_markdown_path, final_md_path)
                results["markdown"] = "moved"
            except:
                data = supabase.storage.from_("screenshots").download(request.temp_markdown_path)
                supabase.storage.from_("screenshots").upload(final_md_path, data, {"content-type": "text/markdown", "upsert": "true"})
                supabase.storage.from_("screenshots").remove([request.temp_markdown_path])
                results["markdown"] = "copied"
        return {"status": "success", "results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/bookmarks/{bookmark_id}")
async def delete_bookmark(bookmark_id: int):
    """
    Удаляет закладку из базы данных и все связанные файлы из Storage.
    """
    try:
        # 1. Удаление записи из таблицы bookmarks
        db_response = supabase.table("bookmarks").delete().eq("id", bookmark_id).execute()
        
        # 2. Удаление файлов из Storage (бакет screenshots)
        # Мы удаляем html, markdown и два варианта скриншота (оригинал и обработанный)
        files_to_delete = [
            f"html/{bookmark_id}.html",
            f"markdown/{bookmark_id}.md",
            f"src_image/{bookmark_id}.png",
            f"image/{bookmark_id}.png"
        ]
        
        # Выполняем удаление файлов залпом
        storage_response = supabase.storage.from_("screenshots").remove(files_to_delete)
        
        logger.info(f"Successfully deleted bookmark {bookmark_id} and checked files: {files_to_delete}")
        
        return {
            "status": "success", 
            "message": f"Bookmark {bookmark_id} deleted from DB and Storage cleanup initiated",
            "db_response": db_response.data,
            "storage_response": storage_response
        }
    except Exception as e:
        logger.error(f"Error during deletion of bookmark {bookmark_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/regenerate_summary")
async def regenerate_summary(request: RegenerateSummaryRequest):
    history_file = ".gemini/hooks/history/last.md"
    summary_file = ".gemini/hooks/history/summary.md"

    if not os.path.exists(history_file):
        return {"success": "error", "error": f"File not found({history_file})"}

    if not os.path.exists(summary_file):
        return {"success": "error", "error": f"File not found({summary_file})"}

    try:
        data_history = ''
        summary_old_data = ''
        summary_old_text = ''
        clean_history_list = []
        clean_summary_list = []
        history_last = []
        history_new = ''
        summary_last = []
        summary_new = ''

        with open(history_file, "r", encoding='utf-8') as f:
            data_history = f.read()

        if data_history:
            data_history_list = data_history.split('------ ')
            if len(data_history_list) > 0:
                for item in data_history_list:
                    if item == '':
                        continue

                    clean_history_list.append(f"------ {item.strip()}")

                    item_list = item.split(' ------')
                    clean_summary_list.append(item_list[1].strip())
            for item in clean_history_list[-request.last_turn:]:
                history_last.append(item)

            for item in clean_summary_list[:-request.last_turn]:
                summary_last.append(item)

        if len(summary_last) > 0:
            summary_new = '\n'.join(summary_last)

            with open(summary_file, "r", encoding='utf-8') as f:
                summary_old_data = f.read()

            if summary_old_data:
                item_list = summary_old_data.split(' ------')
                summary_old_text = item_list[1].strip()

            summary_new_body = await regenerate_new_summary(summary_old_text, summary_new)

            dt = datetime.now()
            formatted = dt.strftime("%H:%M:%S %d.%m.%Y")

            summary_out = ''
            summary_out += f'------ {formatted} ------\n\n'
            summary_out += summary_new_body

            with open(summary_file, "w") as f:
                f.write(summary_out.strip())

        if len(history_last) > 0:
            history_new = '\n\n'.join(history_last)
            with open(history_file, "w") as f:
                f.write(history_new.strip())

        return {"last": request.last_turn, "regenerate": request.regenerate_num}
    except Exception as e:
        logger.error(f"Regenerate summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


app.mount("/static", StaticFiles(directory="static"), name="static")
@app.get("/app")
async def serve_frontend(): return FileResponse("static/index.html")