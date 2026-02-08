import os
import uuid
from collections import defaultdict

from dotenv import load_dotenv
from supabase import create_client, Client
from loguru import logger

NEW_PROCESSED_BOOKMARKS_DIR = "photo"

# Выгружаем переменные окружения
load_dotenv()

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

def upload_to_supabase(file_path: str, storage_path: str):
    """Uploads file to Supabase Storage."""
    with open(file_path, "rb") as f:
        supabase.storage.from_("photogallery").upload(
            path=storage_path,
            file=f,
            file_options={"content-type": "image/jpg", "upsert": "true"}
        )

def count_file_types():
    file_type_counts = defaultdict(int)
    total_files = 0

    if not os.path.isdir(NEW_PROCESSED_BOOKMARKS_DIR):
        print(f"ERROR: Directory '{NEW_PROCESSED_BOOKMARKS_DIR}' not found.")
        return file_type_counts, total_files

    for root, _, files in os.walk(NEW_PROCESSED_BOOKMARKS_DIR):
        for file in files:
            _, ext = os.path.splitext(file)
            ext = ext.lower() # Normalize extension to lowercase
            if ext: # Only count if there is an extension
                file_type_counts[ext] += 1
                if ext == ".jpg":
                    unique_id = uuid.uuid4().hex
                    file_path = os.path.join(root, file)
                    storage_path = f"image/{unique_id}.jpg"
                    # print(file_path, storage_path)
                    upload_to_supabase(file_path, storage_path)
            else:
                file_type_counts["no_extension"] += 1 # Files without an extension
            total_files += 1

    return file_type_counts, total_files

if __name__ == "__main__":
    counts, total = count_file_types()
    print(f"Analysis of file types in '{NEW_PROCESSED_BOOKMARKS_DIR}':")
    for ext, count in sorted(counts.items()):
        print(f"  {ext}: {count}")
    print(f"Total files: {total}")