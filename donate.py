import requests
import time
from main import update_user_subscription

ACCESS_TOKEN = "сюда_вставь_твой_access_token"

# Для хранения последних ID, чтобы не обрабатывать повторно
seen_donations = set()

def check_donations():
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}"
    }
    response = requests.get("https://www.donationalerts.com/api/v1/donations", headers=headers)

    if response.status_code != 200:
        print("⚠️ Ошибка при получении донатов:", response.text)
        return

    data = response.json()
    for donation in data.get("data", []):
        donation_id = donation["id"]
        message = donation.get("message", "").strip().lower()

        if donation_id in seen_donations:
            continue  # Уже обрабатывали
        seen_donations.add(donation_id)

        print(f"🔔 Новый донат: {message}")

        # Разбираем сообщение
        if message.startswith("premium:"):
            try:
                user_id = int(message.split("premium:")[1].strip())
                update_user_subscription(user_id, "premium")
                print(f"✅ Premium активирован для пользователя {user_id}")
            except Exception as e:
                print(f"❌ Ошибка при активации Premium: {e}")

        elif message.startswith("premiumplus:"):
            try:
                user_id = int(message.split("premiumplus:")[1].strip())
                update_user_subscription(user_id, "premium_plus")
                print(f"✅ Premium+ активирован для пользователя {user_id}")
            except Exception as e:
                print(f"❌ Ошибка при активации Premium+: {e}")


if __name__ == "__main__":
    print("🚀 Запущен мониторинг донатов...")
    while True:
        try:
            check_donations()
            time.sleep(15)  # Проверка каждые 15 секунд
        except KeyboardInterrupt:
            print("🛑 Остановлено вручную")
            break
        except Exception as e:
            print(f"⚠️ Ошибка в основном цикле: {e}")
            time.sleep(10)
