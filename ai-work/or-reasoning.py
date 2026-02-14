import sys
import json
import os
import httpx

from openai import OpenAI

from dotenv import load_dotenv
load_dotenv()

# Create a custom httpx client with the proxy settings
custom_http_client = httpx.Client(proxy=os.getenv("PROXY_URL"))

client = OpenAI(
  base_url="https://openrouter.ai/api/v1",
  api_key=os.getenv("OPENROUTER_API_KEY"),
  http_client=custom_http_client,
)

# First API call with reasoning
response = client.chat.completions.create(
  model=os.getenv("AURORA_ALPHA_MODEL_NAME"),
  messages=[
          {
            "role": "user",
            # "content": "How many r's are in the word 'strawberry'?"
            "content": "Почему небо голубое?"
          }
        ],
  extra_body={"reasoning": {"enabled": True}}
)

print(response.choices[0].message.content)

# # Extract the assistant message with reasoning_details
# response = response.choices[0].message

# # Preserve the assistant message with reasoning_details
# messages = [
#   {"role": "user", "content": "How many r's are in the word 'strawberry'?"},
#   {
#     "role": "assistant",
#     "content": response.content,
#     "reasoning_details": response.reasoning_details  # Pass back unmodified
#   },
#   {"role": "user", "content": "Are you sure? Think carefully."}
# ]

# # Second API call - model continues reasoning from where it left off
# response2 = client.chat.completions.create(
#   model="stepfun/step-3.5-flash:free",
#   messages=messages,
#   extra_body={"reasoning": {"enabled": True}}
# )