# llm/model.py
import os
from typing import Dict, Any, List, Optional
import asyncio
from loguru import logger
import httpx

from llm.providers import OllamaProvider, GroqProvider, OpenRouterProvider, DEFAULT_LLM_CONFIG, LLMProvider

# Список всех успешно инициализированных провайдеров в порядке приоритета
available_providers: List[LLMProvider] = []
active_llm_provider: Optional[LLMProvider] = None

async def initialize_llm_providers(provider_order: str):
    """
    Инициализирует список доступных провайдеров согласно заданному порядку.
    """
    global available_providers, active_llm_provider
    available_providers = []
    
    providers_to_check = [p.strip() for p in provider_order.split(',') if p.strip()]

    for provider_name in providers_to_check:
        config = DEFAULT_LLM_CONFIG.get(provider_name)
        if not config:
            logger.warning(f"Неизвестный провайдер LLM в списке: {provider_name}. Пропускаем.")
            continue

        model_class = config["class"]
        model_names = config["model_names"]
        base_url = config.get("base_url")
        api_key = config.get("api_key")

        if api_key is None and provider_name != "ollama":
            logger.warning(f"API ключ для провайдера {provider_name} не найден. Пропускаем.")
            continue

        logger.info(f"Проверяем доступность провайдера: {provider_name}...")
        try:
            if provider_name == "ollama":
                provider_instance = model_class(model_names=model_names, base_url=base_url)
            elif provider_name == "groq":
                proxy_url = os.getenv("PROXY_URL")
                provider_instance = model_class(model_names=model_names, api_key=api_key, base_url=base_url, proxy_url=proxy_url)
            else:
                provider_instance = model_class(model_names=model_names, api_key=api_key, base_url=base_url)

            if await provider_instance.check_health():
                available_providers.append(provider_instance)
                logger.success(f"Провайдер {provider_name} добавлен в список доступных.")
            else:
                logger.warning(f"Провайдер {provider_name} не прошел проверку здоровья.")
        except Exception as e:
            logger.error(f"Ошибка инициализации {provider_name}: {e}")

    if available_providers:
        active_llm_provider = available_providers[0]
        logger.info(f"Первичный активный провайдер: {type(active_llm_provider).__name__}")
    else:
        logger.error("Ни один провайдер не доступен! AI-функции будут отключены.")

async def get_llm_completion(prompt: str, fire: bool = False, **kwargs) -> Dict[str, Any]:
    """
    Умный диспетчер запросов с двойным каскадом переключения (Модели -> Провайдеры).
    
    :param prompt: Текст запроса
    :param fire: Если True, разрешено использовать платный/внешний OpenRouter в каскаде
    :param kwargs: Дополнительные параметры (temperature, max_tokens и т.д.)
    """
    global active_llm_provider
    
    if not available_providers:
        logger.error("Нет доступных провайдеров для выполнения запроса.")
        return {"error": "No available providers"}

    # Создаем временную копию списка провайдеров для обхода в рамках этого запроса
    providers_queue = list(available_providers)
    
    for provider in providers_queue:
        # Проверка флага Fire для OpenRouter
        if isinstance(provider, OpenRouterProvider) and not fire:
            logger.info("Пропускаем OpenRouter (флаг Fire=False)")
            continue

        # Пытаемся выжать всё из текущего провайдера (перебор его моделей)
        provider.reset_model_index() # Начинаем с лучшей модели провайдера
        
        while True:
            current_model = provider.get_current_model()
            provider_name = type(provider).__name__
            
            logger.info(f"Запрос к {provider_name} [модель: {current_model}]...")
            
            try:
                result = await provider.generate_completion(prompt, **kwargs)
                
                # Если в ответе есть ошибка от самого API (например, Rate Limit в JSON)
                if isinstance(result, dict) and "error" in result:
                    error_msg = str(result.get("error"))
                    logger.warning(f"API {provider_name} вернул ошибку: {error_msg}")
                    if provider.switch_to_next_model():
                        continue
                    else:
                        break # Модели у этого провайдера кончились, идем к следующему провайдеру

                return result # УСПЕХ!
                
            except (httpx.HTTPStatusError, httpx.RequestError) as e:
                # Обработка сетевых ошибок и статус-кодов (429, 503 и т.д.)
                status_code = getattr(e.response, 'status_code', None) if hasattr(e, 'response') else None
                logger.warning(f"Ошибка {provider_name} ({status_code or 'Network'}): {e}")
                
                # Если это Rate Limit или ошибка сервера - пробуем сменить модель
                if status_code in [429, 413, 502, 503, 504] or status_code is None:
                    if provider.switch_to_next_model():
                        continue # Пробуем следующую модель
                    else:
                        logger.error(f"У провайдера {provider_name} закончились модели или он недоступен.")
                        break # Идем к следующему провайдеру в списке
                else:
                    # Для других ошибок (например, 401 Unauthorized) не имеет смысла менять модель
                    logger.error(f"Критическая ошибка провайдера {provider_name}, переходим к следующему.")
                    break

    logger.critical("Все доступные модели и провайдеры исчерпаны!")
    return {"error": "All providers failed"}
