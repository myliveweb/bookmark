import requests

# URL сервера
server_url = "http://localhost:8000/completion"

# Данные для запроса
payload = {
    "prompt": "Почему небо голубое?",  # Ваш промпт
    "n_predict": 200,  # Максимальное количество токенов для генерации
    "temperature": 0.2,  # Параметр случайности (0.1-1.0)
    "stop": ["\n", "###"]  # Строки, при которых генерация останавливается
}

# Запрос на сервер  
response = requests.post(server_url, json=payload)

# Парсим ответ
result = response.json()

print("Ответ модели:", result['content'])