from exa_py import Exa

exa = Exa(api_key="057a1915-1d80-496f-9618-746e973395e8") 
result = exa.search(
  "Почему небо голубое",
  type="auto",
  contents={
    "text": True
  }
)
print(result)