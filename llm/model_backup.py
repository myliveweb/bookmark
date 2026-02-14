# llm/model.py
import os
from typing import Dict, Any, List
import asyncio
from loguru import logger

from llm.providers import OllamaProvider, GroqProvider, OpenRouterProvider, DEFAULT_LLM_CONFIG, LLMProvider

active_llm_provider: LLMProvider = None

async def initialize_llm_providers(provider_order: str):
    global active_llm_provider
    providers_to_check = [p.strip() for p in provider_order.split(',') if p.strip()]

    for provider_name in providers_to_check:
        config = DEFAULT_LLM_CONFIG.get(provider_name)
        if not config:
            logger.warning(f"Неизвестный провайдер LLM в списке: {provider_name}. Пропускаем.")
            continue

        model_class = config["class"]
        model_name = config["model_name"]
        base_url = config.get("base_url")
        api_key = config.get("api_key")

        if api_key is None and provider_name != "ollama":
            logger.warning(f"API ключ для провайдера {provider_name} не найден. Пропускаем.")
            continue

        logger.info(f"Пытаемся подключиться к провайдеру LLM: {provider_name} с моделью {model_name}...")
        try:
            # Создаем экземпляр провайдера
            if provider_name == "ollama":
                provider_instance = model_class(model_name=model_name, base_url=base_url)
            elif provider_name == "groq":
                proxy_url = os.getenv("PROXY_URL")
                provider_instance = model_class(model_name=model_name, api_key=api_key, base_url=base_url, proxy_url=proxy_url)
            else:
                provider_instance = model_class(model_name=model_name, api_key=api_key, base_url=base_url)

            if await provider_instance.check_health():
                active_llm_provider = provider_instance
                logger.success(f"Успешно подключено к провайдеру LLM: {provider_name} с моделью {model_name}")
                return
            else:
                logger.warning(f"Провайдер {provider_name} не прошел проверку работоспособности.")
        except Exception as e:
            logger.error(f"Ошибка при проверке провайдера {provider_name}: {e}")

    logger.error("Не удалось подключиться ни к одному LLM провайдеру. AI-функции будут недоступны.")

async def get_llm_completion(prompt: str, **kwargs) -> Dict[str, Any]:
    if not active_llm_provider:
        logger.error("Нет активного LLM провайдера. AI-функции недоступны.")
        return {"error": "No active LLM provider"}
    
    return await active_llm_provider.generate_completion(prompt, **kwargs)
