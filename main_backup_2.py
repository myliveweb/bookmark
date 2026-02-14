import os
import asyncio
import uuid
import json
from typing import List
from datetime import datetime

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

import backend_logic as logic
from models import (
    Bookmark, BookmarkCreate, ResnapRequest, CommitScreenshotRequest, 
    CategoriesResponse, CreateCategoryRequest, ProcessUrlRequest, 
    FinalizeBookmarkRequest, ProcessUrlResponse, AIAnalysisResult, 
    RegenerateSummaryRequest
)

# Инициализация FastAPI
app = FastAPI(title="Bookmark Manager")

# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

        ai_data = await logic.analyze_markdown_content(markdown_text) if markdown_text else {"summary": "", "categories": []}
        
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
    # Start the background task
    background_tasks.add_task(regen_summary_task, request)
    
    # Rust will get this response immediately
    return {"status": "accepted", "info": "Task started in background"}

# Джин не трогай эту функцию, ето писал Босс, ему это нужно
async def regen_summary_task(data: RegenerateSummaryRequest):
    try:
        print(f"last_turn: {data.last_turn}")
        print(f"regenerate_num: {data.regenerate_num}")
        print(f"project_path: {data.project_path}")

        history_file = ".gemini/hooks/history/last.md"
        summary_file = ".gemini/hooks/history/summary.md"

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

        # 2. Достаем 50 сообщений, которые еще НЕ сжаты
        # Используем фильтр по пути и флагу summarized
        history_res = logic.supabase.table('chat_history') \
            .select('id', 'role', 'content') \
            .eq('metadata->>cwd', data.project_path) \
            .eq('summarized', False) \
            .order('created_at') \
            .limit(data.regenerate_num * 2) \
            .execute()

        rows = history_res.data

        if len(rows) < data.last_turn * 2:
            return {"status": "too few records to summarize", "count": len(rows)}

        # Формируем текст истории для LLM
        history_for_ai = ""
        processed_ids = []
        for r in rows[:-data.last_turn * 2]:
            role = "USER" if r['role'] == 'user' else "ASSISTANT"
            history_for_ai += f"{role}: {r['content']}\n"
            processed_ids.append(r['id'])

        n = 0
        for row in processed_ids:
            n += 1
            print(f"{n}: {row}")

        summary_new = '\n'.join(summary_last)

        with open(summary_file, "r", encoding='utf-8') as f:
            summary_old_data = f.read()

        if summary_old_data:
            item_list = summary_old_data.split(' ------')
            summary_old_text = item_list[1].strip()

        summary_res = logic.supabase.table('project_summaries') \
            .select('content', 'iteration') \
            .eq('project_path', data.project_path) \
            .order('created_at', desc=True) \
            .limit(1) \
            .execute()
        
        last_summary_data = summary_res.data[0] if summary_res.data else None
        old_summary = last_summary_data['content'] if last_summary_data else "Начало проекта."
        current_iteration = last_summary_data['iteration'] if last_summary_data else 0

        summary_new_body = await logic.regenerate_new_summary(old_summary, history_for_ai, data.project_path)

        dt = datetime.now()
        formatted = dt.strftime("%H:%M:%S %d.%m.%Y")

        summary_out = ''
        summary_out += f'------ {formatted} ------\n\n'
        summary_out += summary_new_body

        with open(".gemini/hooks/history/summary_test_5.md", "w") as f:
            f.write(summary_out.strip())

        # 4. INSERT новой итерации (Immutable)
        new_iteration = current_iteration + 1
        logic.supabase.table('project_summaries').insert({
            "project_path": data.project_path,
            "content": summary_new_body,
            "iteration": new_iteration,
            "metadata": {
                "source": "automated_regeneration",
                "original_date": formatted,
                "msg_count": len(processed_ids)
            }
        }).execute()

        #     with open(summary_file, "w") as f:
        #         f.write(summary_out.strip())

        # if len(history_last) > 0:
        #     history_new = '\n\n'.join(history_last)
        #     with open(history_file, "w") as f:
        #         f.write(history_new.strip())

    except Exception as e:
        # Запись в лог, чтобы отслеживать причины ошибок
        with open(".gemini/hooks/history/error_task.log", "a+") as f:
            f.write(f"\n[BACKGROUND ERROR] {datetime.now()}: {str(e)}\n")


app.mount("/static", StaticFiles(directory="static"), name="static")
@app.get("/app")
async def serve_frontend(): return FileResponse("static/index.html")
