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
