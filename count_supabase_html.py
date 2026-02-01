import os
from supabase import create_client, Client
from storage3.exceptions import StorageApiError
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# --- Configuration from .env ---
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_KEY")

# Ensure SUPABASE_URL has a trailing slash for storage endpoint compatibility
if SUPABASE_URL and not SUPABASE_URL.endswith('/'):
    SUPABASE_URL += '/'

# --- Hardcoded Project Specifics ---
TARGET_BUCKET = "screenshots"
TARGET_FOLDER = "image" # Counting image files

def main():
    print(f"--- Counting files in Supabase Storage bucket '{TARGET_BUCKET}/{TARGET_FOLDER}/' ---")

    missing_env_vars = []
    if not SUPABASE_URL:
        missing_env_vars.append("SUPABASE_URL")
    if not SUPABASE_KEY:
        missing_env_vars.append("SUPABASE_KEY")

    if missing_env_vars:
        print(f"ERROR: Missing environment variables for Supabase client: {', '.join(missing_env_vars)}")
        print("Please ensure these are set in your .env file or environment.")
        exit(1)

    supabase_client: Client = None
    try:
        supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
        print(f"Successfully initialized Supabase client for URL: {SUPABASE_URL}")
    except Exception as e:
        print(f"ERROR: Failed to initialize Supabase client. Check SUPABASE_URL and SUPABASE_KEY. Error: {e}")
        exit(1)

    try:
        all_files_in_folder = []
        current_offset = 0
        limit = 1000 # Max limit per call as per instruction

        print(f"Fetching files from '{TARGET_BUCKET}/{TARGET_FOLDER}' with pagination (limit={limit})...", flush=True)

        while True:
            # Pass limit, offset, and sortBy within a dictionary as the second argument
            page_files = supabase_client.storage.from_(TARGET_BUCKET).list(
                TARGET_FOLDER, # Path as first argument
                {
                    "limit": limit,
                    "offset": current_offset,
                    "sortBy": {"column": "name", "order": "asc"}, # Sorting for consistent pagination
                }
            )
            
            if not page_files: # No more files
                break
            
            all_files_in_folder.extend(page_files)
            
            if len(page_files) < limit: # Last page
                break
            
            current_offset += limit
            print(f"Fetched {len(all_files_in_folder)} items so far...", flush=True)

        print(f"Total items fetched from Supabase Storage (including placeholders): {len(all_files_in_folder)}", flush=True)
        # print("Raw response from Supabase Storage list method (first few items):")
        # print(all_files_in_folder[:5])
        
        target_files_count = 0
        for item in all_files_in_folder: # This line needs to be indented
            if item['name'].endswith('.png') and item['name'] != '.emptyFolderPlaceholder': # This line also needs to be indented
                target_files_count += 1
        
        print(f"Found {target_files_count} PNG files in '{TARGET_BUCKET}/{TARGET_FOLDER}' in Supabase Storage.", flush=True)

    except StorageApiError as e: # This except block correctly closes the try block above it
        print(f"ERROR: Supabase Storage API Error: {e}")
    except Exception as e:
        print(f"ERROR: An unexpected error occurred: {e}")

if __name__ == "__main__":
    main()