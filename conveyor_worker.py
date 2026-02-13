import asyncio
from loguru import logger
import backend_logic as logic

async def run_worker():
    print("\n[START] Фоновый конвейер запущен")
    print("--------------------------------")
    
    while True:
        try:
            # 1. Ищем одну задачу
            query = logic.supabase.table("bookmarks").select("*")
            query = query.eq("is_processed", False)
            query = query.is_("processing_error", "null")
            query = query.order("id")
            query = query.limit(1)
            response = query.execute()
            
            if not response.data or len(response.data) == 0:
                print("Очередь пуста. Ожидание 10 секунд...")
                await asyncio.sleep(10)
                continue
            
            bookmark = response.data[0]
            b_id = bookmark['id']
            url = bookmark['url']
            
            print("Processing [" + str(b_id) + "]: " + url)
            
            # 2. Запуск логики
            success = await logic.process_bookmark_logic(url, b_id)
            
            if success:
                print("OK: [" + str(b_id) + "] processed.")
            else:
                print("ERROR: [" + str(b_id) + "] failed.")
            
            # 3. Пауза
            await asyncio.sleep(2)
            
        except Exception as e:
            logger.error("Worker Error: " + str(e))
            await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(run_worker())