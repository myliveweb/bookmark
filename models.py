# models.py
from pydantic import BaseModel, HttpUrl
from typing import Optional

class BookmarkCreate(BaseModel):
    title: str
    url: HttpUrl

class Bookmark(BookmarkCreate):
    id: int
