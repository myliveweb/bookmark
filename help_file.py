from bs4 import BeautifulSoup
import re

def analyze_bookmarks(file_path):
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()

    print("\n=== АНАЛИЗ ИЕРАРХИИ (Через отступы) ===")
    
    for line in lines:
        # Ищем папки: <H3 ...>Название</H3>
        folder_match = re.search(r'<(H3|h3)[^>]*>(.*?)</\1>', line)
        if folder_match:
            name = folder_match.group(2)
            # Считаем количество пробелов в начале строки для определения уровня
            indent = len(line) - len(line.lstrip())
            level = indent // 4 # Обычно 4 пробела на уровень
            
            # Попробуем найти ссылки сразу после этой строки до следующего H3
            # Но это сложно. Давайте просто выведем папки и их отступы.
            print(f"{'  ' * level}📁 {name} (отступ: {indent})")

    print("======================================\n")

if __name__ == "__main__":
    analyze_bookmarks('bookmarks/bookmarks_10.02.2026.html')