import os
import time
import httpx

from datetime import datetime, timedelta

from groq import Groq

from dotenv import load_dotenv
load_dotenv()

# Create a custom httpx client with the proxy settings
custom_http_client = httpx.Client(proxy=os.getenv("PROXY_URL"))

client = Groq(
    api_key=os.getenv("GROQ_API_KEY"),
    http_client=custom_http_client,
)

# models = client.models.list()
# print(models)

model_list = [
    "allam-2-7b",
    "groq/compound",
    "groq/compound-mini",
    "llama-3.1-8b-instant",
    "llama-3.3-70b-versatile",
    "meta-llama/llama-4-maverick-17b-128e-instruct",
    "meta-llama/llama-4-scout-17b-16e-instruct",
    "meta-llama/llama-guard-4-12b",
    "meta-llama/llama-prompt-guard-2-22m",
    "meta-llama/llama-prompt-guard-2-86m",
    "moonshotai/kimi-k2-instruct",
    "moonshotai/kimi-k2-instruct-0905",
    "openai/gpt-oss-120b",
    "openai/gpt-oss-20b",
    "openai/gpt-oss-safeguard-20b",
    "qwen/qwen3-32b",
  ]

# Best models
model_list_top = [
    "qwen/qwen3-32b",
    "groq/compound",
    "groq/compound-mini",
    "llama-3.1-8b-instant",
    "llama-3.3-70b-versatile",
    "meta-llama/llama-4-maverick-17b-128e-instruct",
    "meta-llama/llama-4-scout-17b-16e-instruct",
    "moonshotai/kimi-k2-instruct",
    "moonshotai/kimi-k2-instruct-0905",
    "openai/gpt-oss-120b",
    "openai/gpt-oss-20b",
    "openai/gpt-oss-safeguard-20b",
  ]

open('./info-time-groq.md', 'w').close()
open('./info-content-groq.md', 'w').close()
open('./info-error-groq.md', 'w').close()

n = 0
for model in model_list_top:
  start_time = time.perf_counter()
  try:
    response = client.chat.completions.create(
        messages=[
            {
                "role": "user",
                "content": "Почему небо голубое?",
            }
        ],
        model=model,
    )

    dt = datetime.now()
    formatted = dt.strftime("%H:%M:%S %d.%m.%Y")

    duration = time.perf_counter() - start_time

    data_time = f"/*** {formatted} ***/\n- {model} Time work: {duration:.3f} сек.\n\n"
    with open("./info-time-groq.md", "a+") as f:
        f.write(data_time)

    data_content = f"/*** {formatted} ***/\n- {model} Time work: {duration:.3f} сек.\n\n{response.choices[0].message.content}\n\n"
    with open("./info-content-groq.md", "a+") as f:
        f.write(data_content)

    n += 1
    print(f"{n}. End work with model: {model}")
    time.sleep(2)
  except Exception as e:
    print("Error model: ", model)
    data_error = f"/*** {formatted} ***/\n- {model}\n\nError: {e}\n\n"
    with open("./info-error-groq.md", "a+") as f:
        f.write(data_error)
    continue

print("End work with all models")