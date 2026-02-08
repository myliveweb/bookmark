import os
import time
from typing import Any, Literal
from langchain_ollama import ChatOllama
from langchain_core.messages import SystemMessage, HumanMessage
from dotenv import find_dotenv, load_dotenv
from loguru import logger

load_dotenv(find_dotenv())

class ModelOllama:
    def __init__(
        self,
        provider: Literal["deepseek", "qwen", "gemini", "openai", "openai_small"],
        temperature: float = 0.2
    ):
        start_time = time.time()

        if provider == "deepseek":
            model = os.getenv("DEEPSEEK_MODEL_NAME")
        elif provider == "qwen":
            model = os.getenv("QWEN_MODEL_NAME")
        elif provider == "gemini":
            model = os.getenv("GEMINI_MODEL_NAME")
        elif provider == "openai":
            model = os.getenv("OPENAI_120_MODEL_NAME")
        elif provider == "openai_small":
            model = os.getenv("OPENAI_20_MODEL_NAME")
        else:
            raise ValueError(f"Неподдерживаемый провайдер: {provider}")

        logger.info(f"Инициализация ModelOllama ({provider})...")

        self.provider = provider
        self.model = model

        # Добавляем format="json" для гарантированного структурированного вывода
        self.llm = ChatOllama(
            model=self.model,
            temperature=temperature,
            format="json"
        )

        logger.success(f"ModelOllama полностью инициализирована за {time.time() - start_time:.2f} сек.")

    async def send_message_structured_outputs(self, user: str, response_model: Any):
        messages = [
            SystemMessage(content="Ты — эксперт по анализу IT-контента. Извлекай информацию строго по заданной схеме в формате JSON."),
            HumanMessage(content=user)
        ]

        structured_llm = self.llm.with_structured_output(response_model)
        # Используем асинхронный вызов
        res = await structured_llm.ainvoke(messages)
        return res