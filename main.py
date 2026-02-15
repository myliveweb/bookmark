import os
import asyncio
import uuid
import json
from typing import List
from datetime import datetime

from transformers import AutoTokenizer

from fastapi import FastAPI, HTTPException, BackgroundTasks, UploadFile, File
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
from dotenv import load_dotenv # Добавляем загрузку .env
from llm.model import initialize_llm_providers, LLMUnavailableError # Добавляем импорт функций инициализации и ошибки
from llm.model import get_llm_completion # Изменяем импорт, добавляем get_llm_completion


import backend_logic as logic
from models import (
    Bookmark, BookmarkCreate, ResnapRequest, CommitScreenshotRequest, 
    CategoriesResponse, CreateCategoryRequest, ProcessUrlRequest, 
    FinalizeBookmarkRequest, ProcessUrlResponse, AIAnalysisResult, 
    RegenerateSummaryRequest
)

load_dotenv() # Загружаем переменные окружения

# Получаем порядок провайдеров из .env
LLM_PROVIDER_ORDER = os.getenv("LLM_PROVIDER_ORDER", "ollama,groq,openrouter")

# Инициализация FastAPI
app = FastAPI(title="Bookmark Manager")

@app.on_event("startup")
async def startup_event():
    logger.info("Приложение FastAPI запускается...")
    await initialize_llm_providers(LLM_PROVIDER_ORDER)
    logger.info("Приложение FastAPI запущено.")

# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Загружаем токенизатор для Llama 3 (он же для Llama 4)
tokenizer = AutoTokenizer.from_pretrained("unsloth/llama-3-8b-instruct-bnb-4bit")

# --- API Endpoints ---

@app.get("/")
def read_root():
    return {"status": "ok"}

@app.get("/bookmarks", response_model=List[Bookmark])
def get_bookmarks():
    response = logic.supabase.table('bookmarks').select('*').order('id', desc=True).execute()
    if response.data is None:
        raise HTTPException(status_code=500, detail="Could not fetch bookmarks")
    return response.data

@app.post("/bookmarks", response_model=Bookmark, status_code=201)
def create_bookmark(bookmark: BookmarkCreate):
    bookmark_dict = bookmark.model_dump(mode='json')
    response = logic.supabase.table('bookmarks').insert(bookmark_dict).execute()
    if not response.data:
         raise HTTPException(status_code=500, detail="Could not create bookmark")
    return response.data[0]

@app.post("/api/resnap")
async def resnap_bookmark(request: ResnapRequest):
    unique_id = uuid.uuid4().hex
    raw_path = os.path.join(logic.TEMP_DIR, f"{unique_id}_raw.png")
    proc_path = os.path.join(logic.TEMP_DIR, f"{unique_id}.png")
    try:
        await logic.take_screenshot(str(request.url), raw_path)
        await logic.process_image(raw_path, proc_path)
        temp_path = f"temp/{unique_id}.png"
        logic.upload_to_supabase(proc_path, temp_path, "image/png")
        url = logic.supabase.storage.from_("screenshots").get_public_url(temp_path)
        return {"temp_url": url, "temp_filename": temp_path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        for f in [raw_path, proc_path]:
            if os.path.exists(f): os.remove(f)

@app.post("/api/commit-screenshot")
def commit_screenshot(request: CommitScreenshotRequest):
    final_path = f"image/{request.bookmark_id}.png"
    try:
        logic.supabase.storage.from_("screenshots").move(request.temp_filename, final_path)
        return {"status": "success"}
    except:
        data = logic.supabase.storage.from_("screenshots").download(request.temp_filename)
        logic.supabase.storage.from_("screenshots").upload(final_path, data, {"content-type": "image/png", "upsert": "true"})
        logic.supabase.storage.from_("screenshots").remove([request.temp_filename])
        return {"status": "success"}

@app.get("/api/categories", response_model=CategoriesResponse)
def get_categories():
    res = logic.supabase.table("categories").select("name").order("name").execute()
    return {"categories": [r["name"] for r in res.data] if res.data else []}

@app.post("/api/process-url", response_model=ProcessUrlResponse)
async def process_url(request: ProcessUrlRequest):
    unique_id = uuid.uuid4().hex
    raw_path = os.path.join(logic.TEMP_DIR, f"{unique_id}_raw.png")
    proc_path = os.path.join(logic.TEMP_DIR, f"{unique_id}.png")
    html_path = os.path.join(logic.TEMP_DIR, f"{unique_id}.html")
    md_path = os.path.join(logic.TEMP_DIR, f"{unique_id}.md")
    
    try:
        title, html_content = await logic.take_screenshot(str(request.url), raw_path)
        if html_content:
            with open(html_path, "w", encoding="utf-8") as f: f.write(html_content)
        
        if os.path.exists(raw_path): await logic.process_image(raw_path, proc_path)
        
        markdown_text = ""
        if os.path.exists(html_path):
            try:
                res = logic.md_converter.convert(html_path)
                markdown_text = res.text_content
                with open(md_path, "w", encoding="utf-8") as f: f.write(markdown_text)
            except: pass

        try:
            ai_data = await logic.analyze_markdown_content(markdown_text, fire=request.fire) if markdown_text else {"summary": "", "categories": []}
        except LLMUnavailableError:
            logger.warning("ИИ недоступен для ручного запроса. Возвращаем пустые поля.")
            ai_data = {"summary": "", "categories": []}
        
        # Uploads
        paths = {"img": f"temp/{unique_id}.png", "html": f"temp/{unique_id}.html", "md": f"temp/{unique_id}.md"}
        if os.path.exists(proc_path): logic.upload_to_supabase(proc_path, paths["img"], "image/png")
        if os.path.exists(html_path): logic.upload_to_supabase(html_path, paths["html"], "text/html")
        if os.path.exists(md_path): logic.upload_to_supabase(md_path, paths["md"], "text/markdown")

        return {
            "status": "success", "message": "Processed", "suggested_title": title,
            "temp_url": logic.supabase.storage.from_("screenshots").get_public_url(paths["img"]),
            "temp_screenshot_path": paths["img"], "temp_html_path": paths["html"],
            "temp_markdown_path": paths["md"], "uuid": unique_id,
            "suggested_summary": ai_data["summary"], "suggested_categories": ai_data["categories"]
        }
    except Exception as e:
        logger.error(f"API Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        for f in [raw_path, proc_path, html_path, md_path]:
            if os.path.exists(f): os.remove(f)

@app.post("/api/finalize-bookmark")
def finalize_bookmark(request: FinalizeBookmarkRequest):
    id = request.bookmark_id
    try:
        if request.temp_screenshot_path:
            try: logic.supabase.storage.from_("screenshots").move(request.temp_screenshot_path, f"image/{id}.png")
            except: pass
        if request.temp_html_path:
            try: logic.supabase.storage.from_("screenshots").move(request.temp_html_path, f"html/{id}.html")
            except: pass
        if request.temp_markdown_path:
            try: logic.supabase.storage.from_("screenshots").move(request.temp_markdown_path, f"markdown/{id}.md")
            except: pass
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/bookmarks/import")
async def import_bookmarks(file: UploadFile = File(...)):
    """Массовый импорт закладок из HTML-файла."""
    try:
        content = await file.read()
        html_text = content.decode('utf-8', errors='ignore')
        
        # 1. Парсим ссылки из HTML (Разработка и Полезное)
        extracted_links = logic.parse_chrome_bookmarks(html_text)
        if not extracted_links:
            return {"status": "success", "added": 0, "message": "No links found in target folders"}
            
        # 2. Получаем существующие URL, чтобы избежать дублей
        existing_res = logic.supabase.table("bookmarks").select("url").execute()
        existing_urls = {r["url"] for r in existing_res.data} if existing_res.data else set()
        
        # 3. Фильтруем новые
        to_insert = []
        for item in extracted_links:
            if item["url"] not in existing_urls:
                to_insert.append({
                    "url": item["url"],
                    "title": item["title"],
                    "date_add": item["add_date"],
                    "is_processed": False
                })
        
        # 4. Bulk Insert (пачками по 100)
        if to_insert:
            batch_size = 100
            for i in range(0, len(to_insert), batch_size):
                batch = to_insert[i:i + batch_size]
                logic.supabase.table("bookmarks").insert(batch).execute()
        
        return {"status": "success", "added": len(to_insert), "total_found": len(extracted_links)}
    except Exception as e:
        logger.error(f"Import Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/system/conveyor-status")
def get_conveyor_status():
    """Возвращает статистику обработки для индикатора прогресса."""
    try:
        # Всего
        total_res = logic.supabase.table("bookmarks").select("id", count="exact").execute()
        total_count = total_res.count if total_res.count is not None else 0
        
        # Обработано
        proc_res = logic.supabase.table("bookmarks").select("id", count="exact").eq("is_processed", True).execute()
        proc_count = proc_res.count if proc_res.count is not None else 0
        
        # Ошибки
        err_res = logic.supabase.table("bookmarks").select("id", count="exact").not_.is_("processing_error", "null").execute()
        err_count = err_res.count if err_res.count is not None else 0
        
        return {
            "total": total_count,
            "processed": proc_count,
            "errors": err_count
        }
    except Exception as e:
        logger.error(f"Status Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/bookmarks/{id}")
async def delete_bookmark(id: int):
    try:
        logic.supabase.table("bookmarks").delete().eq("id", id).execute()
        files = [f"html/{id}.html", f"markdown/{id}.md", f"image/{id}.png"]
        logic.supabase.storage.from_("screenshots").remove(files)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Джин не трогай этот ендпойнт, ето писал Босс, ему это нужно
@app.post("/api/regenerate_summary")
async def regen_summary(request: RegenerateSummaryRequest, background_tasks: BackgroundTasks):
    print(f"last_turn: {request.last_turn}, regenerate_num: {request.regenerate_num}, project_path: {request.project_path}")
    # print("Временно приостановлено из за окончания лимитов Ollama.")
    # return {"status": "accepted", "info": "Временно приостановлено из за окончания лимитов Ollama."}
    
    # Start the background task
    background_tasks.add_task(regen_summary_task, request)
    
    # Rust will get this response immediately
    return {"status": "accepted", "info": "Task started in background"}

# Джин не трогай эту функцию, ето писал Босс, ему это нужно
async def regen_summary_task(data: RegenerateSummaryRequest):
    try:
        history_file = ".gemini/hooks/history/last.md"
        summary_file = ".gemini/hooks/history/summary.md"
        error_task_file = ".gemini/hooks/history/error_task.log"

        if not os.path.exists(history_file):
            return {"success": "error", "error": f"File not found({history_file})"}

        if not os.path.exists(summary_file):
            return {"success": "error", "error": f"File not found({summary_file})"}

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
            for item in clean_history_list[-data.last_turn:]:
                history_last.append(item)

            for item in clean_summary_list[:-data.last_turn]:
                summary_last.append(item)

        # 2. Достаем все сообщения, которые еще НЕ сжаты
        # Используем фильтр по пути и флагу summarized
        history_res = logic.supabase.table('chat_history') \
            .select('id', 'created_at', 'role', 'content') \
            .eq('metadata->>cwd', data.project_path) \
            .eq('summarized', False) \
            .order('created_at', desc=True) \
            .order('role', desc=True) \
            .limit(data.regenerate_num*2) \
            .execute()

        rows = history_res.data

        if len(rows) < data.last_turn * 2:
            return {"status": "too few records to summarize", "count": len(rows)}

        date_last = None
        # Формируем текст истории для LLM
        history_for_ai = ""
        n = 0
        rows_cut = rows[20:]
        for r in rows_cut:
            n += 1
            num_tokens = logic.count_tokens(r['content'])
            if num_tokens > 800:
                r['content'] = await logic.summary_message(r['content'])
                num_tokens = logic.count_tokens(r['content'])
                await asyncio.sleep(15)
            role = "USER" if r['role'] == 'user' else "ASSISTANT"
            history_for_ai += f"{role}: {r['content']}\n"
            if date_last == None:
                date_last = r['created_at']

        print(date_last)

        summary_res = logic.supabase.table('project_summaries') \
            .select('content', 'iteration') \
            .eq('project_path', data.project_path) \
            .order('created_at', desc=True) \
            .limit(1) \
            .execute()
        
        last_summary_data = summary_res.data[0] if summary_res.data else None
        old_summary = last_summary_data['content'] if last_summary_data else "Начало проекта."
        current_iteration = last_summary_data['iteration'] if last_summary_data else 0

        summary_new_body = await logic.regenerate_new_summary(old_summary, history_for_ai, data.project_path, fire=data.fire)

        with open(".gemini/hooks/history/summary_test.md", "w") as f:
            f.write(summary_new_body)

        dt = datetime.now()
        formatted = dt.strftime("%H:%M:%S %d.%m.%Y")

        # 4. INSERT новой итерации (Immutable)
        new_iteration = current_iteration + 1
        logic.supabase.table('project_summaries').insert({
            "project_path": data.project_path,
            "content": summary_new_body,
            "iteration": new_iteration,
            "metadata": {
                "source": "automated_regeneration",
                "original_date": formatted,
                "msg_count": n
            }
        }).execute()

        # 5. Обновляем флаг summarized в chat_history
        logic.supabase.table('chat_history').update({
            "summarized": True
        }).lte('created_at', date_last).execute()

    except Exception as e:
        # Запись в лог, чтобы отслеживать причины ошибок
        with open(error_task_file, "a+") as f:
            f.write(f"\n[BACKGROUND ERROR] {datetime.now()}: {str(e)}\n")

# Джин не трогай этот ендпойнт, ето писал Босс, ему это нужно
@app.get("/api/boss")
async def boss():
    print("Ручной вызов /api/boss\n\n")

    history_res = logic.supabase.table('chat_history') \
        .select('id', 'created_at', 'role', 'content') \
        .order('created_at', desc=True) \
        .order('role', desc=True) \
        .limit(120) \
        .execute()
    
    rows = history_res.data

    max_content_user = ''
    max_content_assistant = ''
    max_tokens_user = 0
    tokens_user_500 = 0
    tokens_user_1000 = 0
    tokens_user_2000 = 0
    tokens_user_3000 = 0
    tokens_user_0 = 0
    max_tokens_assistant = 0
    tokens_assistant_500 = 0
    tokens_assistant_1000 = 0
    tokens_assistant_2000 = 0
    tokens_assistant_3000 = 0
    tokens_assistant_0 = 0
    content_main = ''
    content_main_user = ''
    content_main_assistant = ''
    n = 0
    for item in rows[20:]:
        num_tokens = logic.count_tokens(item['content'])
        if num_tokens > 800:
            item['content'] = await logic.summary_message(item['content'])
            num_tokens = logic.count_tokens(item['content'])
            await asyncio.sleep(15)
        n += 1
        # print(f"{n}. ID: {item['id']}, Role: {item['role']}, Tokens: {num_tokens}")
        content_main += f"{item['content']}\n\n"

        if item['role'] == 'user':
            content_main_user += f"{item['content']}\n\n"
        elif item['role'] == 'assistant':
            content_main_assistant += f"{item['content']}\n\n"

        if item['role'] == 'user' and max_tokens_user < num_tokens:
            max_content_user = item['content']
            max_tokens_user = num_tokens

        if item['role'] == 'assistant' and max_tokens_assistant < num_tokens:
            max_content_assistant = item['content']
            max_tokens_assistant = num_tokens

        if item['role'] == 'assistant' and num_tokens > 3000:
            tokens_assistant_3000 += 1
        elif item['role'] == 'assistant' and num_tokens > 2000:
            tokens_assistant_2000 += 1
        elif item['role'] == 'assistant' and num_tokens > 1000:
            tokens_assistant_1000 += 1
        elif item['role'] == 'assistant' and num_tokens > 500:
            tokens_assistant_500 += 1
        elif item['role'] == 'assistant' and num_tokens > 0:
            tokens_assistant_0 += 1

        if item['role'] == 'user' and num_tokens > 3000:
            tokens_user_3000 += 1
        elif item['role'] == 'user' and num_tokens > 2000:
            tokens_user_2000 += 1
        elif item['role'] == 'user' and num_tokens > 1000:
            tokens_user_1000 += 1
        elif item['role'] == 'user' and num_tokens > 500:
            tokens_user_500 += 1
        elif item['role'] == 'user' and num_tokens > 0:
            tokens_user_0 += 1

    total_dialog = n/2
    one_percent = total_dialog/100

    summary_res = logic.supabase.table('project_summaries') \
        .select('content', 'iteration') \
        .order('created_at', desc=True) \
        .limit(1) \
        .execute()

    last_summary_data = summary_res.data[0]['content']

    out_content = f"{last_summary_data}\n\n{content_main}"

    print("\nВсе цифры приведены в токенах по модели unsloth/llama-3-8b-instruct-bnb-4bit")
    print("Summary по модели meta-llama/llama-4-scout-17b-16e-instruct")
    print("One Dialog равен 2 сообщения(User -> Assistant)\n")
    print("Total Dialogs:", int(total_dialog))
    print("Old summary Tokens:", logic.count_tokens(last_summary_data))
    print("Messages Tokens:", logic.count_tokens(content_main))
    print("New Out LLM summary Tokens:", logic.count_tokens(out_content))
    print(f"\nUsage Tokens User:\n> 0 and < 500: {tokens_user_0}({tokens_user_0/one_percent:.1f}%)\n> 500 and < 1000: {tokens_user_500}({tokens_user_500/one_percent:.1f}%)\n> 1000 and < 2000: {tokens_user_1000}({tokens_user_1000/one_percent:.1f}%)\n> 2000 and < 3000: {tokens_user_2000}({tokens_user_2000/one_percent:.1f}%)\n> 3000: {tokens_user_3000}({tokens_user_3000/one_percent:.1f}%)")
    print("Max Tokens User:", max_tokens_user)
    print("Total Tokens User:", logic.count_tokens(content_main_user))
    print(f"\nUsage Tokens Assistant:\n> 0 and < 500: {tokens_assistant_0}({tokens_assistant_0/one_percent:.1f}%)\n> 500 and < 1000: {tokens_assistant_500}({tokens_assistant_500/one_percent:.1f}%)\n> 1000 and < 2000: {tokens_assistant_1000}({tokens_assistant_1000/one_percent:.1f}%)\n> 2000 and < 3000: {tokens_assistant_2000}({tokens_assistant_2000/one_percent:.1f}%)\n> 3000: {tokens_assistant_3000}({tokens_assistant_3000/one_percent:.1f}%)")
    print("Max Tokens Assistant:", max_tokens_assistant)
    print("Total Tokens Assistant:", logic.count_tokens(content_main_assistant), "\n")

    with open(".gemini/hooks/history/max_tokens_user.md", "w") as f:
        f.write(max_content_user)

    with open(".gemini/hooks/history/max_tokens_assistant.md", "w") as f:
        f.write(max_content_assistant)

    new_max = await logic.summary_message(max_content_assistant)

    print("\nTry Summary Max message Assistant Tokens\n")
    print("Old Max message Assistant Tokens:", logic.count_tokens(max_content_assistant))
    print("New Max message Assistant Tokens:", logic.count_tokens(new_max))

    with open(".gemini/hooks/history/new_max_tokens_assistant.md", "w") as f:
        f.write(new_max)

    return {"status": "accepted", "info": "Task started in background"}


app.mount("/static", StaticFiles(directory="static"), name="static")
@app.get("/app")
async def serve_frontend(): return FileResponse("static/index.html")
