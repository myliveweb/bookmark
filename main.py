import os
import asyncio
import subprocess
import time
import uuid
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

from models import Bookmark, BookmarkCreate, ResnapRequest, CommitScreenshotRequest, CategoriesResponse, CreateCategoryRequest

# Выгружаем переменные окружения
load_dotenv()

# Инициализация FastAPI
app = FastAPI(title="Bookmark Manager")

# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В продакшене лучше указать конкретные домены
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

async def take_screenshot(url: str, output_path: str):
    """Takes a screenshot using Playwright."""
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

def upload_to_supabase(file_path: str, storage_path: str):
    """Uploads file to Supabase Storage."""
    with open(file_path, "rb") as f:
        supabase.storage.from_("screenshots").upload(
            path=storage_path,
            file=f,
            file_options={"content-type": "image/png", "upsert": "true"}
        )

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
    """
    Takes a new screenshot, processes it, and saves it to a temporary location in Storage.
    Returns the temporary URL.
    """
    unique_id = uuid.uuid4().hex
    raw_screenshot_path = os.path.join(TEMP_DIR, f"{unique_id}_raw.png")
    processed_screenshot_path = os.path.join(TEMP_DIR, f"{unique_id}.png")
    
    try:
        # 1. Take Screenshot
        await take_screenshot(request.url, raw_screenshot_path)
        
        # 2. Process with FFmpeg
        await process_image(raw_screenshot_path, processed_screenshot_path)
        
        # 3. Upload to Supabase Storage (temp folder)
        temp_storage_path = f"temp/{unique_id}.png"
        upload_to_supabase(processed_screenshot_path, temp_storage_path)
        
        # 4. Get Public URL
        # Assuming bucket is public. If not, create signed URL.
        # supabase.storage.from_("screenshots").create_signed_url(temp_storage_path, 3600)
        # For now, construct public URL manually or use get_public_url
        public_url = supabase.storage.from_("screenshots").get_public_url(temp_storage_path)
        
        return {
            "temp_url": public_url,
            "temp_filename": temp_storage_path
        }
        
    except Exception as e:
        logger.error(f"Resnap error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Cleanup local files
        if os.path.exists(raw_screenshot_path):
            os.remove(raw_screenshot_path)
        if os.path.exists(processed_screenshot_path):
            os.remove(processed_screenshot_path)

@app.post("/api/commit-screenshot")
def commit_screenshot(request: CommitScreenshotRequest):
    """
    Moves the temporary screenshot to the permanent location.
    """
    final_path = f"image/{request.bookmark_id}.png"
    
    try:
        # Move file: Supabase Storage move(from, to)
        # Note: 'move' might fail if destination exists? documentation says 'move' acts like rename.
        # If destination exists, we should probably remove it first or use upsert logic.
        # Supabase-py storage move: .move(from_path, to_path)
        
        # Check if exists (optional, but safer to just try move)
        # Actually, let's copy then delete to be safe, or just move.
        # If move fails because dest exists, we might need to delete dest first.
        
        # Try move
        result = supabase.storage.from_("screenshots").move(request.temp_filename, final_path)
        
        # If result is error (sometimes it returns dict with error key, or raises exception)
        # But supabase-py usually raises exception on error or returns data.
        
        return {"status": "success", "final_path": final_path}
        
    except Exception as e:
        # If move failed, maybe because destination exists?
        # Try downloading temp and re-uploading to final? Or delete final and move?
        logger.error(f"Commit error: {e}")
        
        # Fallback: Copy (Download + Upload) if move is flaky on overwrite
        try:
            # Download temp
            temp_data = supabase.storage.from_("screenshots").download(request.temp_filename)
            # Upload to final (upsert=True)
            supabase.storage.from_("screenshots").upload(
                final_path, 
                temp_data, 
                {"content-type": "image/png", "upsert": "true"}
            )
            # Delete temp
            supabase.storage.from_("screenshots").remove([request.temp_filename])
            return {"status": "success", "method": "fallback_copy"}
        except Exception as e2:
            logger.error(f"Fallback commit error: {e2}")
            raise HTTPException(status_code=500, detail=f"Could not commit screenshot: {e}")


@app.post("/api/categories", status_code=201)
def create_category(request: CreateCategoryRequest):
    """
    Creates a new category in the master 'categories' table.
    """
    logger.info(f"Received request to create category: {request.name} with context {request.context_slug}")
    parent_to_assign = "Общие IT-Темы" # Default parent

    if request.context_slug:
        try:
            # Find the parent of the current category
            response = supabase.table("categories").select("parent_category").eq("slug", request.context_slug).single().execute()
            if response.data and response.data.get("parent_category"):
                parent_to_assign = response.data["parent_category"]
        except Exception as e:
            logger.warning(f"Could not find parent for slug {request.context_slug}. Defaulting. Error: {e}")

    new_category_slug = slugify(request.name, replacements=[['+', '-plus-'], ['/', '-or-'], ['(', ''], [')', '']])

    new_category_data = {
        "name": request.name,
        "slug": new_category_slug,
        "parent_category": parent_to_assign,
        "bookmarks_count": 0 # Initialize count to 0, trigger will increment it to 1 on save
    }

    try:
        # Upsert to prevent race conditions or duplicate names
        response = supabase.table("categories").upsert(new_category_data, on_conflict="name").execute()
        
        if not response.data:
            raise HTTPException(status_code=500, detail="Failed to create category in database.")
        
        logger.success(f"Successfully created/upserted category '{request.name}'")
        return response.data[0]
    except Exception as e:
        logger.error(f"Error creating category '{request.name}': {e}")
        # This might happen if the name is not unique and upsert isn't configured for the unique constraint.
        # Let's try to select it to confirm it exists
        try:
            find_response = supabase.table('categories').select('*').eq('name', request.name).single().execute()
            if find_response.data:
                 logger.info("Category already existed, returning existing data.")
                 return find_response.data
            else:
                 raise HTTPException(status_code=500, detail=str(e))
        except Exception as e2:
             raise HTTPException(status_code=500, detail=str(e2))


@app.get("/api/categories", response_model=CategoriesResponse)
def get_categories():
    """
    Returns a list of all unique categories from the master 'categories' table.
    """
    response = supabase.table("categories").select("name").order("name", desc=False).execute()
    
    if not response.data:
        return {"categories": []}
    
    category_names = [row["name"] for row in response.data]
    
    return {"categories": category_names}


# Static files
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/app")
async def serve_frontend():
    return FileResponse("static/index.html")