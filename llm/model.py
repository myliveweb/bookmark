import os
import time
from typing import Any, Literal, Optional
from abc import ABC, abstractmethod
import httpx

from langchain_ollama import ChatOllama
from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from dotenv import find_dotenv, load_dotenv
from loguru import logger

# Загрузка переменных окружения
load_dotenv(find_dotenv())

class BaseModel(ABC):
    """Базовый класс для всех ИИ-провайдеров."""
    
    def __init__(self, provider_name: str, model_name: str, temperature: float = 0.2):
        self.provider_name = provider_name
        self.model_name = model_name
        self.temperature = temperature
        self.llm = None
        logger.info(f"Инициализация {self.__class__.__name__} (Модель: {self.model_name})...")

    @abstractmethod
    def _create_llm(self):
        """Метод для инициализации конкретного LangChain клиента."""
        pass

    async def send_message_structured_outputs(self, user: str, response_model: Any):
        """Единый метод для отправки запросов со структурированным выводом."""
        if not self.llm:
            self._create_llm()
            
        messages = [
            SystemMessage(content="Ты — эксперт по анализу IT-контента. Извлекай информацию строго по заданной схеме в формате JSON."),
            HumanMessage(content=user)
        ]

        # Настраиваем структурированный вывод через LangChain
        structured_llm = self.llm.with_structured_output(response_model)
        
        start_time = time.perf_counter()
        logger.info(f"[{self.provider_name.upper()}] Отправка запроса к модели {self.model_name}...")
        
        try:
            # Используем асинхронный вызов ainvoke
            res = await structured_llm.ainvoke(messages)
            
            duration = time.perf_counter() - start_time
            logger.success(f"[{self.provider_name.upper()}] Ответ от {self.model_name} получен за {duration:.2f} сек.")
            return res
        except Exception as e:
            duration = time.perf_counter() - start_time
            logger.error(f"[{self.provider_name.upper()}] Ошибка через {duration:.2f} сек.: {e}")
            raise

class ModelOllama(BaseModel):
    def __init__(self, provider: str = "gemini", temperature: float = 0.2):
        # Совместимость со старым вызовом через provider
        if provider == "deepseek":
            model_name = os.getenv("DEEPSEEK_MODEL_NAME")
        elif provider == "qwen":
            model_name = os.getenv("QWEN_MODEL_NAME")
        elif provider == "gemini":
            model_name = os.getenv("GEMINI_MODEL_NAME")
        else:
            model_name = os.getenv("GEMINI_MODEL_NAME", "gemini-3-flash-preview:cloud")
            
        super().__init__("ollama", model_name, temperature)

    def _create_llm(self):
        self.llm = ChatOllama(
            model=self.model_name,
            temperature=self.temperature,
            format="json"
        )

class ModelGroq(BaseModel):
    def __init__(self, temperature: float = 0.2):
        model_name = os.getenv("GROQ_MODEL_NAME", "llama-3.3-70b-versatile")
        super().__init__("groq", model_name, temperature)

    def _create_llm(self):
        proxy_url = os.getenv("PROXY_URL")
        
        # Для Groq в РФ обязательно используем прокси
        client_args = {}
        if proxy_url:
            # Используем AsyncClient для асинхронной работы LangChain (ainvoke)
            client_args["http_async_client"] = httpx.AsyncClient(proxy=proxy_url)
            
        self.llm = ChatGroq(
            model=self.model_name,
            temperature=self.temperature,
            api_key=os.getenv("GROQ_API_KEY"),
            **client_args
        )

class ModelOpenRouter(BaseModel):
    def __init__(self, temperature: float = 0.2):
        model_name = os.getenv("OPENROUTER_MODEL_NAME", "qwen/qwen3-vl-235b-a22b-thinking")
        super().__init__("openrouter", model_name, temperature)

    def _create_llm(self):
        model_kwargs = {}
        # Если модель поддерживает thinking (рассуждения), включаем их через extra_body
        if "thinking" in self.model_name:
            model_kwargs["extra_body"] = {"reasoning": {"enabled": True}}
            
        self.llm = ChatOpenAI(
            model=self.model_name,
            temperature=self.temperature,
            openai_api_key=os.getenv("OPENROUTER_API_KEY"),
            openai_api_base="https://openrouter.ai/api/v1",
            **model_kwargs
        )

def get_llm_engine():
    """Фабрика для получения активного ИИ-двигателя на основе .env."""
    provider = os.getenv("ACTIVE_AI_PROVIDER", "ollama").lower()
    
    if provider == "ollama":
        return ModelOllama()
    elif provider == "groq":
        return ModelGroq()
    elif provider == "openrouter":
        return ModelOpenRouter()
    else:
        logger.warning(f"Провайдер '{provider}' не найден. Откат к Ollama.")
        return ModelOllama()
