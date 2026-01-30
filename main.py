import os
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from typing import List
from dotenv import load_dotenv
from supabase import create_client, Client

from models import Bookmark, BookmarkCreate

# Выгружаем переменные окружения
load_dotenv()

# Инициализация FastAPI
app = FastAPI(title="Bookmark Manager")

# Подключение к Supabase (как и было)
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Supabase credentials not found in .env file")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- API Endpoints ---

@app.get("/")
def read_root():
    """Эндпоинт для проверки работоспособности."""
    return {"status": "ok"}

@app.get("/bookmarks", response_model=List[Bookmark])
def get_bookmarks():
    """Получить все закладки."""
    response = supabase.table('bookmarks').select('*').order('id', desc=True).execute()
    if response.data is None:
        raise HTTPException(status_code=500, detail="Could not fetch bookmarks")
    return response.data

@app.post("/bookmarks", response_model=Bookmark, status_code=201)
def create_bookmark(bookmark: BookmarkCreate):
    """Создать новую закладку."""
    bookmark_dict = bookmark.model_dump(mode='json')
    response = supabase.table('bookmarks').insert(bookmark_dict).execute()

    if not response.data:
         raise HTTPException(status_code=500, detail="Could not create bookmark")

    return response.data[0]

# Размещаем в конце, чтобы API эндпоинты имели приоритет

app.mount("/static", StaticFiles(directory="static"), name="static")



@app.get("/app")

async def serve_frontend():

    return FileResponse("static/index.html")
