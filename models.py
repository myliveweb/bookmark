# models.py
from pydantic import BaseModel, HttpUrl
from typing import Optional

class BookmarkCreate(BaseModel):
    title: str
    url: HttpUrl
    add_date: int

class Bookmark(BookmarkCreate):
    id: int
