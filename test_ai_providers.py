import os
import asyncio
from pydantic import BaseModel, Field
from llm.model import get_llm_engine
from loguru import logger

class TestSchema(BaseModel):
    answer: str = Field(description="Краткий ответ на вопрос")

async def test_provider(provider_name: str):
    logger.info(f"--- Тестирование провайдера: {provider_name} ---")
    # Подменяем переменную окружения для теста
    os.environ["ACTIVE_AI_PROVIDER"] = provider_name
    
    try:
        # Получаем двигатель через фабрику
        engine = get_llm_engine()
        logger.info(f"Выбран класс: {engine.__class__.__name__}")
        logger.info(f"Модель из ENV: {engine.model_name}")
        
        # Проверяем создание объекта LLM (без отправки запроса)
        engine._create_llm()
        if engine.llm:
            logger.success(f"Объект Chat-модели для {provider_name} успешно создан.")
        else:
            logger.error(f"Провайдер {provider_name} НЕ инициализирован.")
            
    except Exception as e:
        logger.error(f"Ошибка при тестировании {provider_name}: {e}")

async def main():
    providers = ["ollama", "groq", "openrouter"]
    for p in providers:
        await test_provider(p)

if __name__ == "__main__":
    asyncio.run(main())
