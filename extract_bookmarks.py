import json
import os
from bs4 import BeautifulSoup

TARGET_FOLDERS = ["Услуги", "Разработка", "Полезное"]
INPUT_FILE = "bookmarks/bookmarks_10.02.2026.html"
OUTPUT_FILE = "bookmarks/temp_extracted_links.json"

def extract_links():
    if not os.path.exists(INPUT_FILE):
        print(f"Error: {INPUT_FILE} not found.")
        return

    with open(INPUT_FILE, 'r', encoding='utf-8', errors='ignore') as f:
        soup = BeautifulSoup(f, 'html.parser')

    extracted_data = {}
    all_folders = soup.find_all('h3')
    
    for h3 in all_folders:
        folder_name = h3.get_text().strip()
        if folder_name in TARGET_FOLDERS:
            print(f"Reading folder: {folder_name}")
            parent_dl = h3.find_next('dl')
            if parent_dl:
                links = parent_dl.find_all('a')
                count = 0
                for a in links:
                    url = a.get('href')
                    if not url or url.startswith('chrome://') or url.startswith('about:'):
                        continue
                    
                    title = a.get_text().strip()
                    try:
                        add_date = int(a.get('add_date', 0))
                    except:
                        add_date = 0
                    
                    if url in extracted_data:
                        if add_date > extracted_data[url]['add_date']:
                            extracted_data[url] = {"title": title, "add_date": add_date}
                    else:
                        extracted_data[url] = {"title": title, "add_date": add_date}
                    count += 1
                print(f"Found links: {count}")

    final_list = [{"url": url, "title": info["title"], "add_date": info["add_date"]} for url, info in extracted_data.items()]

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(final_list, f, ensure_ascii=False, indent=2)

    print("\nExtraction complete!")
    print(f"Total unique links: {len(final_list)}")
    print(f"Saved to: {OUTPUT_FILE}")

if __name__ == "__main__":
    extract_links()