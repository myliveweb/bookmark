import os
from collections import defaultdict

NEW_PROCESSED_BOOKMARKS_DIR = "frontend/nuxt-app/public/processed_bookmarks"

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