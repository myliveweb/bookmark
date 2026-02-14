import sys
import json
import os
import httpx

from openai import OpenAI

from dotenv import load_dotenv
load_dotenv()

client = OpenAI(
  base_url="https://openrouter.ai/api/v1",
  api_key=os.getenv("OPENROUTER_API_KEY"),
)

# First API call with reasoning
response = client.chat.completions.create(
  extra_headers={
    "HTTP-Referer": "", # Optional. Site URL for rankings on openrouter.ai.
    "X-Title": "", # Optional. Site title for rankings on openrouter.ai.
  },
  extra_body={},
  model=os.getenv("MISTRAL_MODEL_NAME"),
  messages=[
    {
      "role": "user",
      "content": "Почему небо голубое?"
    }
  ]
)

print(response.choices[0].message.content)