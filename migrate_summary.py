import psycopg2
import os
import json

# Настройки
DB_CONFIG = "postgresql://postgres:postgres@127.0.0.1:54322/postgres?sslmode=disable"
SUMMARY_FILE = ".gemini/hooks/history/summary.md"
CWD = "/home/sergey/pet/uv/bookmark"

def migrate():
    if not os.path.exists(SUMMARY_FILE):
        return

    with open(SUMMARY_FILE, "r", encoding="utf-8") as f:
        data = f.read()

    # Парсим: разделитель " ------" отделяет дату от контента
    parts = data.split(" ------")
    if len(parts) < 2:
        return

    # Извлекаем дату из начала: "------ 21:52:39 09.02.2026"
    raw_date = parts[0].replace("------ ", "").strip()
    summary_content = parts[1].strip()

    try:
        conn = psycopg2.connect(DB_CONFIG)
        cur = conn.cursor()

        # SQL под твою схему
        query = """
        INSERT INTO public.project_summaries (project_path, content, iteration, metadata, created_at)
        VALUES (%s, %s, %s, %s, TO_TIMESTAMP(%s, 'HH24:MI:SS DD.MM.YYYY'))
        """

        metadata = json.dumps({
            "source": "initial_migration",
            "original_date": raw_date
        })

        cur.execute(query, (CWD, summary_content, 1, metadata, raw_date))
        
        conn.commit()
        print(f"✅ Миграция завершена. Итерация 1 для {CWD} в базе.")

    except Exception as e:
        print(f"❌ Ошибка: {e}")
    finally:
        if 'conn' in locals():
            cur.close()
            conn.close()

if __name__ == "__main__":
    migrate()
