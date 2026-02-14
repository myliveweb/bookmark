# Автоматическое переключение LLM-провайдеров: Ollama, Groq, OpenRouter Implementation Plan

> **Для Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Реализовать автоматическое определение доступного LLM-провайдера (Ollama, Groq, OpenRouter) при старте FastAPI с заданным порядком приоритета и использованием соответствующих моделей.

**Architecture:** Будут созданы классы-обёртки для каждого провайдера LLM с методом проверки работоспособности. При старте FastAPI будет выполняться асинхронная проверка доступности провайдеров в заданном порядке. Первый доступный провайдер будет устанавливаться как активный, а его конфигурация будет использоваться для всех последующих LLM-запросов. Логика `backend_logic.py` будет модифицирована для использования этого динамически выбранного провайдера.

**Tech Stack:** FastAPI, Python (requests/httpx), Ollama API, Groq API, OpenRouter API.

---

### Task 1: Создание базовой абстракции для LLM-провайдеров

**Files:**
- Create: `llm/providers.py`

**Step 1: Создать файл `llm/providers.py` с абстрактным базовым классом и классами для Ollama, Groq, OpenRouter.**
Этот файл будет содержать базовый класс `LLMProvider` и его конкретные реализации для каждого провайдера. Каждый класс будет иметь методы для проверки работоспособности (`check_health`) и генерации ответов (`generate_completion`).

```python
# llm/providers.py
from abc import ABC, abstractmethod
import os
from typing import Dict, Any, List
import httpx
import json

class LLMProvider(ABC):
    """Абстрактный базовый класс для всех LLM провайдеров."""
    def __init__(self, model_name: str, base_url: str):
        self.model_name = model_name
        self.base_url = base_url

    @abstractmethod
    async def check_health(self) -> bool:
        """Проверяет доступность и работоспособность провайдера."""
        pass

    @abstractmethod
    async def generate_completion(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """Генерирует ответ от LLM."""
        pass

    def get_config(self) -> Dict[str, str]:
        """Возвращает конфигурацию провайдера."""
        return {"model_name": self.model_name, "base_url": self.base_url}

class OllamaProvider(LLMProvider):
    def __init__(self, model_name: str, base_url: str = "http://localhost:11434"):
        super().__init__(model_name, base_url)
        self.client = httpx.AsyncClient()

    async def check_health(self) -> bool:
        try:
            # Проверяем, что Ollama запущен и модель доступна
            response = await self.client.post(f"{self.base_url}/api/generate", json={"model": self.model_name, "prompt": "test"}, timeout=5)
            response.raise_for_status()
            # Если ответ успешный, но без контента, это нормально для проверки
            return True
        except (httpx.RequestError, httpx.HTTPStatusError):
            return False

    async def generate_completion(self, prompt: str, **kwargs) -> Dict[str, Any]:
        full_prompt = {"model": self.model_name, "prompt": prompt, "stream": False, **kwargs}
        response = await self.client.post(f"{self.base_url}/api/generate", json=full_prompt)
        response.raise_for_status()
        return response.json()

class GroqProvider(LLMProvider):
    def __init__(self, model_name: str, api_key: str, base_url: str = "https://api.groq.com/openai/v1"):
        super().__init__(model_name, base_url)
        self.api_key = api_key
        self.client = httpx.AsyncClient(headers={"Authorization": f"Bearer {self.api_key}"})

    async def check_health(self) -> bool:
        if not self.api_key:
            return False
        try:
            # Проверяем доступность API и модели
            response = await self.client.post(
                f"{self.base_url}/chat/completions",
                json={
                    "model": self.model_name,
                    "messages": [{"role": "user", "content": "hello"}],
                    "max_tokens": 1
                },
                timeout=5
            )
            response.raise_for_status()
            return True
        except (httpx.RequestError, httpx.HTTPStatusError):
            return False

    async def generate_completion(self, prompt: str, **kwargs) -> Dict[str, Any]:
        messages = [{"role": "user", "content": prompt}]
        response = await self.client.post(
            f"{self.base_url}/chat/completions",
            json={"model": self.model_name, "messages": messages, **kwargs}
        )
        response.raise_for_status()
        return response.json()

class OpenRouterProvider(LLMProvider):
    def __init__(self, model_name: str, api_key: str, base_url: str = "https://openrouter.ai/api/v1"):
        super().__init__(model_name, base_url)
        self.api_key = api_key
        self.client = httpx.AsyncClient(headers={"Authorization": f"Bearer {self.api_key}", "HTTP-Referer": "http://localhost:8000", "X-Title": "Bookmark AI"})

    async def check_health(self) -> bool:
        if not self.api_key:
            return False
        try:
            # Проверяем доступность API и модели
            response = await self.client.post(
                f"{self.base_url}/chat/completions",
                json={
                    "model": self.model_name,
                    "messages": [{"role": "user", "content": "hello"}],
                    "max_tokens": 1
                },
                timeout=5
            )
            response.raise_for_status()
            return True
        except (httpx.RequestError, httpx.HTTPStatusError):
            return False

    async def generate_completion(self, prompt: str, **kwargs) -> Dict[str, Any]:
        messages = [{"role": "user", "content": prompt}]
        response = await self.client.post(
            f"{self.base_url}/chat/completions",
            json={"model": self.model_name, "messages": messages, **kwargs}
        )
        response.raise_for_status()
        return response.json()

# Глобальная переменная для хранения активного провайдера
active_llm_provider: LLMProvider = None

# Конфигурация провайдеров по умолчанию
DEFAULT_LLM_CONFIG = {
    "ollama": {
        "model_name": "gemini-3-flash-preview:cloud",
        "base_url": os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        "class": OllamaProvider
    },
    "groq": {
        "model_name": "meta-llama/llama-4-scout-17b-16e-instruct",
        "api_key": os.getenv("GROQ_API_KEY"),
        "base_url": os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1"),
        "class": GroqProvider
    },
    "openrouter": {
        "model_name": "stepfun/step-3.5-flash:free",
        "api_key": os.getenv("OPENROUTER_API_KEY"),
        "base_url": os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
        "class": OpenRouterProvider
    }
}
```

### Task 2: Создание тестов для LLM-провайдеров

**Files:**
- Create: `tests/test_llm_providers.py`

**Step 1: Создать файл `tests/test_llm_providers.py` с тестами для `llm/providers.py`**
```python
import pytest
import os
from unittest.mock import AsyncMock, patch, MagicMock
from llm.providers import OllamaProvider, GroqProvider, OpenRouterProvider
import httpx # Import httpx to use its exceptions

# Helper to create a mock httpx.Response object
class MockResponse:
    def __init__(self, status_code: int = 200, json_data: dict = None, exc: Exception = None):
        self.status_code = status_code
        self._json_data = json_data if json_data is not None else {}
        self._exc = exc

    def json(self) -> dict:
        return self._json_data

    def raise_for_status(self):
        if self._exc:
            raise self._exc
        # Default behavior is to do nothing on success

@pytest.fixture
def mock_httpx_async_client():
    """Fixture to mock httpx.AsyncClient().post to return a MockResponse."""
    with patch('httpx.AsyncClient') as mock_client_class:
        mock_instance = AsyncMock() # This mocks `self.client`
        mock_client_class.return_value = mock_instance # When httpx.AsyncClient() is called, it returns mock_instance
        yield mock_instance

@pytest.mark.asyncio
async def test_ollama_provider_health(mock_httpx_async_client):
    ollama_provider = OllamaProvider(model_name="gemini-3-flash-preview:cloud")
    ollama_provider.client = mock_httpx_async_client

    # Test successful health check
    mock_httpx_async_client.post.return_value = MockResponse(200, {"status": "ok"})
    assert await ollama_provider.check_health() is True
    mock_httpx_async_client.post.assert_called_once()
    mock_httpx_async_client.post.reset_mock()

    # Test failed health check (connection error)
    mock_httpx_async_client.post.side_effect = httpx.RequestError("Connection refused", request=MagicMock())
    assert await ollama_provider.check_health() is False
    mock_httpx_async_client.post.assert_called_once()
    mock_httpx_async_client.post.reset_mock()
    mock_httpx_async_client.post.side_effect = None # Clear side_effect for next test block

    # Test failed health check (HTTP status error)
    mock_httpx_async_client.post.return_value = MockResponse(400, exc=httpx.HTTPStatusError("Bad Request", request=MagicMock(), response=MagicMock()))
    assert await ollama_provider.check_health() is False
    mock_httpx_async_client.post.assert_called_once()
    mock_httpx_async_client.post.reset_mock()


@pytest.mark.asyncio
async def test_groq_provider_health(mock_httpx_async_client):
    os.environ["GROQ_API_KEY"] = "mock_groq_key"
    groq_provider = GroqProvider(model_name="meta-llama/llama-4-scout-17b-16e-instruct", api_key=os.environ["GROQ_API_KEY"])
    groq_provider.client = mock_httpx_async_client

    # Test successful health check
    mock_httpx_async_client.post.return_value = MockResponse(200, {"status": "ok"})
    assert await groq_provider.check_health() is True
    mock_httpx_async_client.post.assert_called_once()
    mock_httpx_async_client.post.reset_mock()

    # Test failed health check (no API key)
    groq_provider_no_key = GroqProvider(model_name="test", api_key=None)
    assert await groq_provider_no_key.check_health() is False # This should not call post

    # Test failed health check (connection error)
    mock_httpx_async_client.post.side_effect = httpx.RequestError("Connection refused", request=MagicMock())
    assert await groq_provider.check_health() is False
    mock_httpx_async_client.post.assert_called_once()
    mock_httpx_async_client.post.reset_mock()
    mock_httpx_async_client.post.side_effect = None

    # Test failed health check (HTTP status error)
    mock_httpx_async_client.post.return_value = MockResponse(400, exc=httpx.HTTPStatusError("Bad Request", request=MagicMock(), response=MagicMock()))
    assert await groq_provider.check_health() is False
    mock_httpx_async_client.post.assert_called_once()
    mock_httpx_async_client.post.reset_mock()

    del os.environ["GROQ_API_KEY"] # Clean up

@pytest.mark.asyncio
async def test_openrouter_provider_health(mock_httpx_async_client):
    os.environ["OPENROUTER_API_KEY"] = "mock_openrouter_key"
    openrouter_provider = OpenRouterProvider(model_name="stepfun/step-3.5-flash:free", api_key=os.environ["OPENROUTER_API_KEY"])
    openrouter_provider.client = mock_httpx_async_client

    # Test successful health check
    mock_httpx_async_client.post.return_value = MockResponse(200, {"status": "ok"})
    assert await openrouter_provider.check_health() is True
    mock_httpx_async_client.post.assert_called_once()
    mock_httpx_async_client.post.reset_mock()

    # Test failed health check (no API key)
    openrouter_provider_no_key = OpenRouterProvider(model_name="test", api_key=None)
    assert await openrouter_provider_no_key.check_health() is False

    # Test failed health check (connection error)
    mock_httpx_async_client.post.side_effect = httpx.RequestError("Connection refused", request=MagicMock())
    assert await openrouter_provider.check_health() is False
    mock_httpx_async_client.post.assert_called_once()
    mock_httpx_async_client.post.reset_mock()
    mock_httpx_async_client.post.side_effect = None

    # Test failed health check (HTTP status error)
    mock_httpx_async_client.post.return_value = MockResponse(400, exc=httpx.HTTPStatusError("Bad Request", request=MagicMock(), response=MagicMock()))
    assert await openrouter_provider.check_health() is False
    mock_httpx_async_client.post.assert_called_once()
    mock_httpx_async_client.post.reset_mock()

    del os.environ["OPENROUTER_API_KEY"] # Clean up

@pytest.mark.asyncio
async def test_ollama_provider_generate(mock_httpx_async_client):
    mock_httpx_async_client.post.return_value = MockResponse(200, {"response": "test response from ollama"})
    ollama_provider = OllamaProvider(model_name="gemini-3-flash-preview:cloud")
    ollama_provider.client = mock_httpx_async_client
    result = await ollama_provider.generate_completion(prompt="hello")
    assert result["response"] == "test response from ollama"

@pytest.mark.asyncio
async def test_groq_provider_generate(mock_httpx_async_client):
    mock_httpx_async_client.post.return_value = MockResponse(200, {"choices": [{"message": {"content": "test response from groq"}}]})
    os.environ["GROQ_API_KEY"] = "mock_groq_key"
    groq_provider = GroqProvider(model_name="meta-llama/llama-4-scout-17b-16e-instruct", api_key=os.environ["GROQ_API_KEY"])
    groq_provider.client = mock_httpx_async_client
    result = await groq_provider.generate_completion(prompt="hello")
    assert result["choices"][0]["message"]["content"] == "test response from groq"
    del os.environ["GROQ_API_KEY"]

@pytest.mark.asyncio
async def test_openrouter_provider_generate(mock_httpx_async_client):
    mock_httpx_async_client.post.return_value = MockResponse(200, {"choices": [{"message": {"content": "test response from openrouter"}}]})
    os.environ["OPENROUTER_API_KEY"] = "mock_openrouter_key"
    openrouter_provider = OpenRouterProvider(model_name="stepfun/step-3.5-flash:free", api_key=os.environ["OPENROUTER_API_KEY"])
    openrouter_provider.client = mock_httpx_async_client
    result = await openrouter_provider.generate_completion(prompt="hello")
    assert result["choices"][0]["message"]["content"] == "test response from openrouter"
    del os.environ["OPENROUTER_API_KEY"]
```