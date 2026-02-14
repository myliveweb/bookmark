import sys
import json
import os
import time
import httpx

from datetime import datetime, timedelta

from openai import OpenAI

from dotenv import load_dotenv
load_dotenv()

client = OpenAI(
  base_url="https://openrouter.ai/api/v1",
  api_key=os.getenv("OPENROUTER_API_KEY"),
)

model_list = [
    "stepfun/step-3.5-flash:free",
    "arcee-ai/trinity-large-preview:free", # Small
    "openrouter/aurora-alpha",
    "tngtech/deepseek-r1t2-chimera:free",
    "z-ai/glm-4.5-air:free",
    "deepseek/deepseek-r1-0528:free",
    "nvidia/nemotron-3-nano-30b-a3b:free",
    "tngtech/tng-r1t-chimera:free",
    "openai/gpt-oss-120b:free",
    "upstage/solar-pro-3:free",
    "meta-llama/llama-3.3-70b-instruct:free",
    "arcee-ai/trinity-mini:free",
    "qwen/qwen3-vl-235b-a22b-thinking",
    "qwen/qwen3-coder:free",
    "nvidia/nemotron-nano-12b-v2-vl:free",
    "nvidia/nemotron-nano-9b-v2:free",
    "openai/gpt-oss-20b:free",
    "qwen/qwen3-next-80b-a3b-instruct:free",
    "google/gemma-3-27b-it:free",
    "cognitivecomputations/dolphin-mistral-24b-venice-edition:free",
    "qwen/qwen3-vl-30b-a3b-thinking",
    "mistralai/mistral-small-3.1-24b-instruct:free",
    "nousresearch/hermes-3-llama-3.1-405b:free",
    "qwen/qwen3-4b:free",
  ]

# Best models
model_list_top = [
    "stepfun/step-3.5-flash:free",
    "openrouter/aurora-alpha",
    "qwen/qwen3-vl-235b-a22b-thinking",
    "qwen/qwen3-vl-30b-a3b-thinking",
    "arcee-ai/trinity-large-preview:free", # Small
  ]

open('./info-time-openrouter.md', 'w').close()
open('./info-content-openrouter.md', 'w').close()
open('./info-error-openrouter.md', 'w').close()

n = 0
for model in model_list_top:
  start_time = time.perf_counter()
  try:
    response = client.chat.completions.create(
      model=model,
      messages=[
              {
                "role": "user",
                "content": "Почему небо голубое?"
              }
            ],
      extra_body={"reasoning": {"enabled": True}}
    )

    dt = datetime.now()
    formatted = dt.strftime("%H:%M:%S %d.%m.%Y")

    duration = time.perf_counter() - start_time

    data_time = f"/*** {formatted} ***/\n- {model} Time work: {duration:.3f} сек.\n\n"
    with open("./info-time-openrouter.md", "a+") as f:
        f.write(data_time)

    data_content = f"/*** {formatted} ***/\n- {model} Time work: {duration:.3f} сек.\n\n{response.choices[0].message.content}\n\n"
    with open("./info-content-openrouter.md", "a+") as f:
        f.write(data_content)

    n += 1
    print(f"{n}. End work with model: {model}")
    time.sleep(2)
  except Exception as e:
    data_error = f"/*** {formatted} ***/\n- {model}\n\nError: {e}\n\n"
    with open("./info-error-openrouter.md", "a+") as f:
        f.write(data_error)
    continue

print("End work with all models")