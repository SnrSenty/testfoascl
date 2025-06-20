from fastapi import FastAPI, Request
from main import update_user_subscription
import logging

app = FastAPI()

@app.post("/donate")
async def handle_donation(request: Request):
    data = await request.json()

    # Сообщение с доната, сюда человек вводит: premium:123456789
    message = data.get("message", "").lower()
    logging.info(f"Донат получен: {message}")

    if message.startswith("premium:"):
        try:
            user_id = int(message.split("premium:")[1].strip())
            update_user_subscription(user_id, "premium")
            return {"status": "ok", "user_id": user_id, "type": "premium"}
        except Exception as e:
            return {"status": "error", "reason": str(e)}

    elif message.startswith("premiumplus:"):
        try:
            user_id = int(message.split("premiumplus:")[1].strip())
            update_user_subscription(user_id, "premium_plus")
            return {"status": "ok", "user_id": user_id, "type": "premium_plus"}
        except Exception as e:
            return {"status": "error", "reason": str(e)}

    return {"status": "ignored"}
