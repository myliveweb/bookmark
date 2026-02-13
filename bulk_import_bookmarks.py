import json
import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
INPUT_FILE = "bookmarks/new_links_to_import.json"

def bulk_import():
    if not os.path.exists(INPUT_FILE):
        print("Error: Input file not found.")
        return

    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        new_links = json.load(f)
    
    total = len(new_links)
    if total == 0:
        print("No new links to import.")
        return

    print("Starting import of " + str(total) + " items...")

    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    data = []
    for item in new_links:
        data.append({
            "title": item["title"],
            "url": item["url"],
            "date_add": item["add_date"],
            "is_processed": False
        })

    batch_size = 50
    count = 0
    for i in range(0, len(data), batch_size):
        batch = data[i : i + batch_size]
        try:
            supabase.table("bookmarks").insert(batch).execute()
            count += len(batch)
            print("Progress: " + str(count) + "/" + str(total))
        except Exception as e:
            print("Error: " + str(e))
            break

    print("Done! Imported: " + str(count))

if __name__ == "__main__":
    bulk_import()