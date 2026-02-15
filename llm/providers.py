from abc import ABC, abstractmethod
import os
from typing import Dict, Any, List, Optional
import httpx
import json
from loguru import logger

class LLMProvider(ABC):
    """Абстрактный базовый класс для всех LLM провайдеров с поддержкой каскада моделей."""
    def __init__(self, model_names: List[str], base_url: str):
        self.model_names = model_names
        self.base_url = base_url
        self.current_model_index = 0

    def get_current_model(self) -> str:
        """Возвращает имя текущей активной модели."""
        if 0 <= self.current_model_index < len(self.model_names):
            return self.model_names[self.current_model_index]
        return self.model_names[0] if self.model_names else "unknown"

    def switch_to_next_model(self) -> bool:
        """Переключает на следующую модель в списке. Возвращает False, если модели закончились."""
        if self.current_model_index < len(self.model_names) - 1:
            self.current_model_index += 1
            logger.info(f"Переключено на следующую модель: {self.get_current_model()}")
            return True
        return False

    def reset_model_index(self):
        """Сбрасывает индекс модели на начальный."""
        self.current_model_index = 0

    @abstractmethod
    async def check_health(self) -> bool:
        """Проверяет доступность и работоспособность провайдера (по первой модели)."""
        pass

    @abstractmethod
    async def generate_completion(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """Генерирует ответ от LLM текущей моделью."""
        pass

    def get_config(self) -> Dict[str, Any]:
        """Возвращает конфигурацию провайдера."""
        return {
            "current_model": self.get_current_model(),
            "all_models": self.model_names,
            "base_url": self.base_url
        }

class OllamaProvider(LLMProvider):
    def __init__(self, model_names: List[str], base_url: str = "http://localhost:11434"):
        super().__init__(model_names, base_url)
        self.client = httpx.AsyncClient(timeout=60.0)

    async def check_health(self) -> bool:
        try:
            # Проверяем по первой модели в списке
            model = self.model_names[0]
            response = await self.client.post(
                f"{self.base_url}/api/generate", 
                json={"model": model, "prompt": "test", "max_tokens": 1}, 
                timeout=5
            )
            return response.status_code == 200
        except Exception:
            return False

    async def generate_completion(self, prompt: str, **kwargs) -> Dict[str, Any]:
        full_prompt = {
            "model": self.get_current_model(), 
            "prompt": prompt, 
            "stream": False, 
            **kwargs
        }
        response = await self.client.post(f"{self.base_url}/api/generate", json=full_prompt)
        response.raise_for_status()
        return response.json()

class GroqProvider(LLMProvider):
    def __init__(self, model_names: List[str], api_key: str, base_url: str = "https://api.groq.com/openai/v1", proxy_url: str = None):
        super().__init__(model_names, base_url)
        self.api_key = api_key
        client_args = {
            "headers": {"Authorization": f"Bearer {self.api_key}"},
            "timeout": 30.0
        }
        if proxy_url:
            client_args["proxy"] = proxy_url
        self.client = httpx.AsyncClient(**client_args)

    async def check_health(self) -> bool:
        if not self.api_key:
            return False
        try:
            response = await self.client.post(
                f"{self.base_url}/chat/completions",
                json={
                    "model": self.model_names[0],
                    "messages": [{"role": "user", "content": "hi"}],
                    "max_tokens": 1
                },
                timeout=10
            )
            return response.status_code == 200
        except Exception:
            return False

    async def generate_completion(self, prompt: str, **kwargs) -> Dict[str, Any]:
        messages = [{"role": "user", "content": prompt}]
        response = await self.client.post(
            f"{self.base_url}/chat/completions",
            json={"model": self.get_current_model(), "messages": messages, **kwargs}
        )
        response.raise_for_status()
        return response.json()

class OpenRouterProvider(LLMProvider):
    def __init__(self, model_names: List[str], api_key: str, base_url: str = "https://openrouter.ai/api/v1"):
        super().__init__(model_names, base_url)
        self.api_key = api_key
        self.client = httpx.AsyncClient(
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "HTTP-Referer": "http://localhost:8000",
                "X-Title": "Bookmark AI"
            },
            timeout=60.0
        )

    async def check_health(self) -> bool:
        if not self.api_key:
            return False
        try:
            response = await self.client.post(
                f"{self.base_url}/chat/completions",
                json={
                    "model": self.model_names[0],
                    "messages": [{"role": "user", "content": "hi"}],
                    "max_tokens": 1
                },
                timeout=10
            )
            return response.status_code == 200
        except Exception:
            return False

    async def generate_completion(self, prompt: str, **kwargs) -> Dict[str, Any]:
        messages = [{"role": "user", "content": prompt}]
        response = await self.client.post(
            f"{self.base_url}/chat/completions",
            json={"model": self.get_current_model(), "messages": messages, **kwargs}
        )
        response.raise_for_status()
        return response.json()

# Конфигурация провайдеров со списками моделей
DEFAULT_LLM_CONFIG = {
    "ollama": {
        "model_names": [
            "gemini-3-flash-preview:cloud",
            "qwen3-vl:235b-instruct-cloud",
            "gpt-oss:120b-cloud",
            "kimi-k2:1t-cloud"
        ],
        "base_url": os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        "class": OllamaProvider
    },
    "groq": {
        "model_names": [
            "meta-llama/llama-4-scout-17b-16e-instruct",
            "llama-3.3-70b-versatile",
            "llama-3.1-8b-instant",
            "mixtral-8x7b-32768"
        ],
        "api_key": os.getenv("GROQ_API_KEY"),
        "base_url": os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1"),
        "class": GroqProvider
    },
    "openrouter": {
        "model_names": [
            "stepfun/step-3.5-flash:free",
            "google/gemini-2.0-flash-exp:free",
            "mistralai/pixtral-12b:free",
            "meta-llama/llama-3.1-8b-instruct:free"
        ],
        "api_key": os.getenv("OPENROUTER_API_KEY"),
        "base_url": os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
        "class": OpenRouterProvider
    }
}
