import json
import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
EXTRACTED_FILE = "bookmarks/temp_extracted_links.json"
NEW_LINKS_FILE = "bookmarks/new_links_to_import.json"

def filter_links():
    if not os.path.exists(EXTRACTED_FILE):
        print("Error: Extracted file not found.")
        return

    with open(EXTRACTED_FILE, 'r', encoding='utf-8') as f:
        extracted_links = json.load(f)
    
    print(f"Loaded {len(extracted_links)} links.")

    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    existing_urls = set()
    offset = 0
    limit = 1000
    
    while True:
        res = supabase.table("bookmarks").select("url").range(offset, offset + limit - 1).execute()
        if not res.data: break
        for row in res.data:
            existing_urls.add(row['url'].rstrip('/'))
        if len(res.data) < limit: break
        offset += limit

    print(f"Found {len(existing_urls)} URLs in DB.")

    new_links = []
    for item in extracted_links:
        url = item['url'].rstrip('/')
        if url not in existing_urls:
            new_links.append(item)

    with open(NEW_LINKS_FILE, 'w', encoding='utf-8') as f:
        json.dump(new_links, f, ensure_ascii=False, indent=2)

    print(f"New links count: {len(new_links)}")
    print(f"Result saved to {NEW_LINKS_FILE}")

if __name__ == "__main__":
    filter_links()