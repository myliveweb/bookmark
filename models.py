# models.py
from pydantic import BaseModel, HttpUrl
from typing import Optional, List

class BookmarkCreate(BaseModel):
    title: str
    url: HttpUrl
    add_date: int

class Bookmark(BookmarkCreate):
    id: int

class ResnapRequest(BaseModel):
    url: HttpUrl
    bookmark_id: int

class CommitScreenshotRequest(BaseModel):
    bookmark_id: int
    temp_filename: str

class CategoriesResponse(BaseModel):
    categories: List[str]

class CreateCategoryRequest(BaseModel):
    name: str
    context_slug: Optional[str] = None
