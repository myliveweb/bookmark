import os
import httpx

from groq import Groq

from dotenv import load_dotenv
load_dotenv()

# Create a custom httpx client with the proxy settings
custom_http_client = httpx.Client(proxy=os.getenv("PROXY_URL"))

client = Groq(
    api_key=os.getenv("GROQ_API_KEY"),
    http_client=custom_http_client,
)

chat_completion = client.chat.completions.create(
    messages=[
        {
            "role": "user",
            "content": "Почему небо голубое?",
        }
    ],
    model="llama-3.3-70b-versatile",
)

print(chat_completion.choices[0].message.content)