# Этот файл для получения access_token по OAuth2. 
# Используй одноразово для получения токена — дальше только ACCESS_TOKEN.

import requests

client_id = "вставь_сюда_свой_client_id"
client_secret = "вставь_сюда_свой_client_secret"
code = "сюда_вставь_одноразовый_code_из_редиректа"
redirect_uri = "http://localhost:001"  # тот же, что указывал при создании приложения

url = "https://www.donationalerts.com/oauth/token"

data = {
    "grant_type": "authorization_code",
    "client_id": client_id,
    "client_secret": client_secret,
    "redirect_uri": redirect_uri,
    "code": code,
}

response = requests.post(url, data=data)
print(response.json())