import asyncio
import os
from dotenv import load_dotenv
from supabase import create_client, AsyncClient
from loguru import logger

# --- Настройка ---
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Учетные данные Supabase не найдены в файле .env")

supabase: AsyncClient = create_client(SUPABASE_URL, SUPABASE_KEY)

async def run_recalculation():
    """Вызывает RPC-функцию в Supabase для пересчета всех счетчиков категорий."""
    logger.info("Вызов функции в базе данных 'recalculate_all_category_counts'...")

    try:
        # Вызываем функцию, созданную в базе данных
        supabase.rpc('recalculate_all_category_counts', {}).execute()

        logger.success("Функция в базе данных успешно выполнена. Счетчики должны быть обновлены.")

    except Exception as e:
        logger.error(f"Произошла ошибка при вызове RPC-функции: {e}")


async def main():
    await run_recalculation()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nПрограмма прервана пользователем (Ctrl+C)")
    except Exception as e:
        logger.exception("Произошла глобальная ошибка в работе программы:")
