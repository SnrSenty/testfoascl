import requests

client_id = "15368"
client_secret = "C0EpMnPGwUlsaJz0Gsuo0Gz0pehNPh6xm9YcbTEj"
code = "def50200797ca4b006252cdcbb7a8e472c8341ba013de25511b599ab33016e3243ab444d99f427c7748e3e60cf443ad909868d6ebee6b1ae6354ee7c3838d6f43d140bc89b01e6c0b30d03c08e3e16e8a82364847fc2c85a6b39501af93614eaef317beea67f66590a3ac2016bf61c628f300f81d97d910045d0884f2a02ff7b2c52b1e7fc93fdb88589b4a96d12171138db7b5b471cd04debe8117549e2fab0569c7ba70dc5ae479a3df9dc66451041c67abd751867b461013398761dbb9ddd5720fbd72ab4d1438c270652336b80960aad1c3ece3755522676892b37b902c289ba60f83907c8abefcbd9721c8ed99c651fc9e6b05b9af86a917c2e6b9de19f2205ef2edede0315b73e0834b546b2d832eaafb5308bd4f4c689eb02aac7a9fb2e59ad149d290ab48eb17a4fb6d4a30c7e89e81782f7f4f6a7fe12999694e920020a4796157613e1bff80a08254240489b87647b1bc044c480e52d0141bc88de"
redirect_uri = "http://localhost:001"  # тот же, что указывал

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
