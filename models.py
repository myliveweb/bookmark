# models.py
from pydantic import BaseModel, HttpUrl, Field, AliasChoices
from typing import Optional, List

class AIAnalysisResult(BaseModel):
    categories: List[str] = Field(
        validation_alias=AliasChoices('categories', 'classification'),
        description="Список 1-3 релевантных IT-категорий из предложенного списка"
    )
    summary: str = Field(description="Краткое описание контента на русском языке (2-3 предложения)")

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

class ProcessUrlRequest(BaseModel):
    url: HttpUrl

class ProcessUrlResponse(BaseModel):
    status: str
    message: str
    suggested_title: str
    temp_url: Optional[str]
    temp_screenshot_path: str
    temp_html_path: str
    temp_markdown_path: str
    uuid: str
    suggested_summary: Optional[str] = None
    suggested_categories: List[str] = []

class FinalizeBookmarkRequest(BaseModel):
    bookmark_id: int
    temp_screenshot_path: Optional[str] = None
    temp_html_path: Optional[str] = None
    temp_markdown_path: Optional[str] = None

class RegenerateSummaryRequest(BaseModel):
    last_turn: int
    regenerate_num: int