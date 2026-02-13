import asyncio
import time
import sys
from loguru import logger
from backend_logic import process_bookmark_full_cycle, supabase

async def run_conveyor():
    """Воркер для точечной обработки закладок с categories=[]."""
    logger.info("🚀 Хирургический конвейер V2 запущен.")
    logger.info("🎯 Цель: ВСЕ закладки с categories=[], игнорируя старые ошибки.")
    
    # Память воркера, чтобы не крутить одну и ту же ошибку по кругу в рамках одного запуска
    attempted_ids = set()

    while True:
        try:
            # 1. Запрашиваем только те, где категории пустые []
            query = supabase.table("bookmarks") \
                .select("id, url") \
                .eq("categories", "[]") \
                .order("id", desc=False)
            
            # Если у нас уже есть список 'отказников', исключаем их из текущего запроса,
            # чтобы найти следующую годную закладку.
            if attempted_ids:
                query = query.not_.in_("id", list(attempted_ids))
                
            response = query.limit(1).execute()
            bookmarks = response.data

            if not bookmarks:
                if attempted_ids:
                    logger.info(f"🏁 Все доступные цели ({len(attempted_ids)}) были опробованы. Новых нет.")
                else:
                    logger.info("😴 Очередь пуста. Жду 30 секунд...")
                await asyncio.sleep(30)
                # Очищаем память раз в цикл сна, чтобы дать шанс на переповтор через время
                attempted_ids.clear()
                continue

            bookmark = bookmarks[0]
            b_id = bookmark["id"]
            url = bookmark["url"]

            # Запоминаем, что мы взялись за этот ID
            attempted_ids.add(b_id)

            # 2. Запускаем цикл обработки
            try:
                # Теперь с 'llama-3.1-8b-instant' и обрезкой текста всё должно летать
                await process_bookmark_full_cycle(b_id, url)
            except Exception as e:
                logger.error(f"❌ Ошибка на #{b_id}: {e}")

            # 3. ПАУЗА (Groq RPM safety)
            wait_time = 3.0
            logger.info(f"⏳ Пауза {wait_time} сек...")
            await asyncio.sleep(wait_time)

        except Exception as main_e:
            logger.critical(f"🚨 КРИТИЧЕСКАЯ ОШИБКА: {main_e}")
            await asyncio.sleep(10)

if __name__ == "__main__":
    try:
        asyncio.run(run_conveyor())
    except KeyboardInterrupt:
        logger.warning("\n🛑 Конвейер остановлен.")
        sys.exit(0)
