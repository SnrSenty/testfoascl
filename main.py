import logging
import datetime
import sqlite3
import time
import requests
import random
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from collections import defaultdict

CHANNEL_IDS = ["@aisocialnull", "@digital_v_teme"]
AD_CHANNEL_ID = "@channelaibotad"
BOT_TOKEN = "7920009590:AAFG6T5NHqron96oyUSST_nXJhsqz3J4TeE"
ADMIN_ID_LIST = [5191720312, 7960796663]
DB_FILE = "users.db"
PREMIUM_DAYS = 30
PREMIUM_PLUS_DAYS = 30  
PREMIUM_PLUS_TOKENS = 500

# DonationAlerts 
DONATIONALERTS_PREMIUM_LINK = "https://www.donationalerts.com/r/yourpremiumlink"
DONATIONALERTS_PREMIUM_PLUS_LINK = "https://www.donationalerts.com/r/yourpremiumpluslink"

AI_MODELS = {
    "chatgpt_4_1_nano": {
        "title": "ChatGPT 4.1 nano",
        "price": 10,
        "type": "text",
        "api_url": "",
        "api_key": "",
        "model_id": "gpt-4.1-nano"
    },
    "gemini_flash": {
        "title": "Gemini Flash",
        "price": 15,
        "type": "text",
        "api_url": "",
        "api_key": "",
        "model_id": "gemini-flash"
    },
    "chatgpt_3_5_turbo": {
        "title": "ChatGPT 3.5 turbo",
        "price": 15,
        "type": "text",
        "api_url": "",
        "api_key": "",
        "model_id": "gpt-3.5-turbo"
    },
    "qwen_2_5_max": {
        "title": "Qwen 2.5 Max",
        "price": 20,
        "type": "text",
        "api_url": "",
        "api_key": "",
        "model_id": "qwen-2.5-max"
    },
    "deepseek_v3": {
        "title": "Deepseek v3",
        "price": 25,
        "type": "text",
        "api_url": "",
        "api_key": "",
        "model_id": "deepseek-chat-v3"
    },
    "deepseek_r1": {
        "title": "Deepseek R1",
        "price": 15,
        "type": "text",
        "api_url": "",
        "api_key": "",
        "model_id": "deepseek-r1"
    },
    "dall_e": {
        "title": "DALL-E (Генерация изображений)",
        "price": 60,
        "type": "image",
        "api_url": "",
        "api_key": "",
        "model_id": "dall-e"
    }
}

LIMITS = {
    "free": {"tokens": 100, "word_limit": 70, "ref_bonus": 25},
    "premium": {"tokens": 300, "word_limit": 70, "ref_bonus": 50},
    "premium_plus": {"tokens": PREMIUM_PLUS_TOKENS, "word_limit": 70, "ref_bonus": 75}
}

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
conn = sqlite3.connect(DB_FILE, check_same_thread=False, timeout=30)
conn.execute("PRAGMA journal_mode=WAL;")
conn.execute("PRAGMA synchronous=NORMAL;")

def execute_db(query, params=(), fetchone=False, commit=False):
    for attempt in range(5):
        try:
            cur = conn.cursor()
            cur.execute(query, params)
            if commit:
                conn.commit()
            return cur.fetchone() if fetchone else cur.fetchall()
        except sqlite3.OperationalError as e:
            if "database is locked" in str(e):
                time.sleep(0.1)
            else:
                raise
    raise sqlite3.OperationalError("Database locked after retries")

def init_db():
    execute_db("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            tokens INTEGER DEFAULT 0,
            words INTEGER DEFAULT 0,
            premium BOOLEAN DEFAULT 0,
            premium_plus BOOLEAN DEFAULT 0,
            expires_at TEXT,
            last_reset TEXT,
            model TEXT DEFAULT 'chatgpt_4_1_nano',
            referred_by INTEGER,
            ref_count INTEGER DEFAULT 0,
            last_message_time INTEGER DEFAULT 0,
            last_active_date TEXT
        )
    """, commit=True)
    execute_db("""
        CREATE TABLE IF NOT EXISTS referrals (
            user_id INTEGER PRIMARY KEY,
            referral_code TEXT,
            referred_by INTEGER,
            joined_at TEXT
        )
    """, commit=True)
    execute_db("""
        CREATE TABLE IF NOT EXISTS ads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_url TEXT NOT NULL,
            send_time TEXT NOT NULL,
            start_date TEXT NOT NULL,
            end_date TEXT NOT NULL,
            total_shows INTEGER DEFAULT 0,
            enabled BOOLEAN DEFAULT 1,
            last_sent_date TEXT
        )
    """, commit=True)
    execute_db("""
        CREATE TABLE IF NOT EXISTS stat (
            key TEXT PRIMARY KEY,
            value INTEGER DEFAULT 0
        )
    """, commit=True)
    execute_db("""
        CREATE TABLE IF NOT EXISTS quest_channels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            channel_url TEXT UNIQUE NOT NULL,
            bonus INTEGER DEFAULT 15
        )
    """, commit=True)
    execute_db("""
        CREATE TABLE IF NOT EXISTS quest_claims (
            user_id INTEGER,
            channel_url TEXT,
            claimed_at TEXT,
            PRIMARY KEY(user_id, channel_url)
        )
    """, commit=True)
    execute_db("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_ads_post_url ON ads(post_url)
    """, commit=True)

def migrate_db():
    columns = execute_db("PRAGMA table_info(users)", fetchone=False)
    colnames = [c[1] for c in columns]
    alter_stmts = []
    if "premium_plus" not in colnames:
        alter_stmts.append("ALTER TABLE users ADD COLUMN premium_plus BOOLEAN DEFAULT 0")
    if "model" not in colnames:
        alter_stmts.append("ALTER TABLE users ADD COLUMN model TEXT DEFAULT 'chatgpt_4_1_nano'")
    if "referred_by" not in colnames:
        alter_stmts.append("ALTER TABLE users ADD COLUMN referred_by INTEGER")
    if "ref_count" not in colnames:
        alter_stmts.append("ALTER TABLE users ADD COLUMN ref_count INTEGER DEFAULT 0")
    if "last_message_time" not in colnames:
        alter_stmts.append("ALTER TABLE users ADD COLUMN last_message_time INTEGER DEFAULT 0")
    if "last_active_date" not in colnames:
        alter_stmts.append("ALTER TABLE users ADD COLUMN last_active_date TEXT")
    for stmt in alter_stmts:
        try:
            execute_db(stmt, commit=True)
        except Exception as e:
            if "duplicate column name" in str(e):
                continue
            else:
                raise
    ads_columns = execute_db("PRAGMA table_info(ads)", fetchone=False)
    ads_colnames = [c[1] for c in ads_columns]
    if "enabled" not in ads_colnames:
        execute_db("ALTER TABLE ads ADD COLUMN enabled BOOLEAN DEFAULT 1", commit=True)
    if "last_sent_date" not in ads_colnames:
        execute_db("ALTER TABLE ads ADD COLUMN last_sent_date TEXT", commit=True)
    quest_columns = execute_db("PRAGMA table_info(quest_channels)", fetchone=False)
    quest_colnames = [c[1] for c in quest_columns]
    if "bonus" not in quest_colnames:
        execute_db("ALTER TABLE quest_channels ADD COLUMN bonus INTEGER DEFAULT 15", commit=True)
    execute_db("""
        CREATE TABLE IF NOT EXISTS quest_claims (
            user_id INTEGER,
            channel_url TEXT,
            claimed_at TEXT,
            PRIMARY KEY(user_id, channel_url)
        )
    """, commit=True)

def get_user_data(user_id):
    row = execute_db("SELECT * FROM users WHERE user_id = ?", (user_id,), fetchone=True)
    if row:
        return {
            "tokens": row[1],
            "words": row[2],
            "premium": bool(row[3]),
            "premium_plus": bool(row[4]),
            "expires_at": datetime.datetime.strptime(row[5], "%Y-%m-%d %H:%M:%S") if row[5] else None,
            "last_reset": datetime.datetime.strptime(row[6], "%Y-%m-%d %H:%M:%S") if row[6] else None,
            "model": row[7] or "chatgpt_4_1_nano",
            "referred_by": row[8],
            "ref_count": row[9] or 0,
            "last_message_time": row[10] or 0,
            "last_active_date": datetime.datetime.strptime(row[11], "%Y-%m-%d") if row[11] else datetime.datetime.now(),
        }
    return None

def update_user_data(user_id, data):
    execute_db("""
        INSERT OR REPLACE INTO users (user_id, tokens, words, premium, premium_plus, expires_at, last_reset, model, referred_by, ref_count, last_message_time, last_active_date)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        user_id,
        data.get("tokens", 0),
        data.get("words", 0),
        int(data.get("premium", False)),
        int(data.get("premium_plus", False)),
        data["expires_at"].strftime("%Y-%m-%d %H:%M:%S") if data.get("expires_at") else None,
        data["last_reset"].strftime("%Y-%m-%d %H:%M:%S") if data.get("last_reset") else None,
        data.get("model", "chatgpt_4_1_nano"),
        data.get("referred_by"),
        data.get("ref_count", 0),
        data.get("last_message_time", 0),
        data["last_active_date"].strftime("%Y-%m-%d"),
    ), commit=True)

def get_or_create_referral_code(user_id):
    code = execute_db("SELECT referral_code FROM referrals WHERE user_id = ?", (user_id,), fetchone=True)
    if code and code[0]:
        return code[0]
    new_code = f"ref{user_id}{random.randint(1000,9999)}"
    execute_db("INSERT OR REPLACE INTO referrals (user_id, referral_code, joined_at) VALUES (?, ?, date('now'))", (user_id, new_code), commit=True)
    return new_code

def set_user_referred_by(user_id, referred_by):
    execute_db("UPDATE users SET referred_by = ? WHERE user_id = ?", (referred_by, user_id), commit=True)

def add_ref_count(user_id, add):
    execute_db("UPDATE users SET ref_count = ref_count + ? WHERE user_id = ?", (add, user_id), commit=True)

def add_user_tokens(user_id, tokens):
    execute_db("UPDATE users SET tokens = tokens + ? WHERE user_id = ?", (tokens, user_id), commit=True)

def is_admin(user_id):
    return user_id in ADMIN_ID_LIST

def give_premium_to_admins():
    now = datetime.datetime.now()
    expires = now + datetime.timedelta(days=PREMIUM_PLUS_DAYS)
    for admin_id in ADMIN_ID_LIST:
        data = get_user_data(admin_id) or {
            "tokens": LIMITS['premium_plus']['tokens'],
            "words": 0,
            "premium": True,
            "premium_plus": True,
            "last_reset": now,
            "model": "chatgpt_4_1_nano",
            "ref_count": 0,
            "last_message_time": 0,
            "last_active_date": now,
        }
        data["premium"] = True
        data["premium_plus"] = True
        data["expires_at"] = expires
        data["tokens"] = LIMITS['premium_plus']['tokens']
        update_user_data(admin_id, data)

def get_quest_channels():
    return execute_db("SELECT channel_url, bonus FROM quest_channels ORDER BY id", fetchone=False)

def add_quest_channel(channel_url, bonus=15):
    execute_db("INSERT OR IGNORE INTO quest_channels (channel_url, bonus) VALUES (?, ?)", (channel_url, bonus), commit=True)

def del_quest_channel(channel_url):
    execute_db("DELETE FROM quest_channels WHERE channel_url = ?", (channel_url,), commit=True)

def quest_already_claimed(user_id, channel_url):
    return bool(execute_db("SELECT 1 FROM quest_claims WHERE user_id = ? AND channel_url = ?", (user_id, channel_url), fetchone=True))

def set_quest_claimed(user_id, channel_url):
    execute_db("INSERT OR REPLACE INTO quest_claims (user_id, channel_url, claimed_at) VALUES (?, ?, ?)", (user_id, channel_url, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")), commit=True)

async def check_subscription(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    try:
        for channel in CHANNEL_IDS:
            chat_member = None
            if channel.startswith('-100'):
                chat_id = int(channel)
                chat_member = await context.bot.get_chat_member(chat_id, user_id)
            else:
                try:
                    chat = await context.bot.get_chat(channel)
                    chat_member = await context.bot.get_chat_member(chat.id, user_id)
                except Exception as e:
                    logging.error(f"Ошибка при получении участника канала {channel}: {e}")
            if not chat_member or chat_member.status not in ["member", "administrator", "creator"]:
                return False
        return True
    except Exception as e:
        logging.error(f"Ошибка проверки подписки: {e}")
        return False

async def check_quest_subscription(user_id: int, context: ContextTypes.DEFAULT_TYPE, channel_url: str) -> bool:
    try:
        username = channel_url.replace("https://t.me/", "").replace("@", "").split("/")[0]
        chat = await context.bot.get_chat(f"@{username}")
        chat_member = await context.bot.get_chat_member(chat.id, user_id)
        return chat_member.status in ["member", "administrator", "creator"]
    except Exception as e:
        logging.error(f"Ошибка проверки подписки квест-канала {channel_url}: {e}")
        return False

user_context = defaultdict(list)

def get_model_buttons(selected_model=None):
    text_buttons = []
    img_buttons = []
    for key, model in AI_MODELS.items():
        btn_text = f"{'✅ ' if key == selected_model else ''}{model['title']} — {model['price']} ток."
        if model["type"] == "text":
            text_buttons.append([InlineKeyboardButton(btn_text, callback_data=f"choose_model_{key}")])
        elif model["type"] == "image":
            img_buttons.append([InlineKeyboardButton(btn_text, callback_data=f"choose_model_{key}")])
    return text_buttons, img_buttons

def get_settings_menu():
    return [
        [InlineKeyboardButton("🤖 Генерация текста", callback_data="choose_text_model_menu")],
        [InlineKeyboardButton("🖼️ Генерация изображений", callback_data="choose_image_model_menu")],
        [InlineKeyboardButton("🎁 Бонусы и задания", callback_data="bonuses_info")],
        [InlineKeyboardButton("🔙 Назад к профилю", callback_data="back_to_profile")]
    ]


async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data = get_user_data(user_id)
    if not user_data:
        await context.bot.send_message(user_id, "❌ Ошибка. Пользователь не найден.")
        return
    subscribed = await check_subscription(user_id, context)
    username = update.effective_user.username or "Не указан"
    is_premium = user_data.get("premium", False)
    is_premium_plus = user_data.get("premium_plus", False)
    expires_at = user_data.get("expires_at")
    days_left = (expires_at - datetime.datetime.now()).days if is_premium and expires_at else 0
    tokens = user_data.get("tokens", LIMITS["free"]["tokens"])
    model_key = user_data.get("model", "chatgpt_4_1_nano")
    model = AI_MODELS.get(model_key, AI_MODELS["chatgpt_4_1_nano"])["title"]
    text = (
        f"👤 <b>Профиль пользователя</b> @{username}\n"
        f"📆 <b>Последняя активность:</b> {user_data.get('last_active_date').strftime('%d.%m.%Y')}\n"
        f"⭐️ <b>Статус:</b> {'<b>Premium+</b> 👑' if is_premium_plus else ('<b>Premium</b> ✅' if is_premium else '<b>Базовый</b> ❌')}\n"
        + (f"⏳ <b>Дней Premium осталось:</b> <b>{days_left}</b>\n" if is_premium else "")
        + f"💸 <b>Токенов:</b> <b>{tokens}</b>\n"
        f"🤖 <b>Текущая модель:</b> <b>{model}</b>\n"
        f"📢 <b>Подписка на основные каналы:</b> {'Активна ✅' if subscribed else 'Неактивна ❌'}\n\n"
        "ℹ️ <i>Токены обновляются раз в 24 часа. Используйте их для общения с ИИ и генерации изображений. "
        "Премиум даёт больше токенов и бонусов!</i>\n"
    )
    reply_keyboard = [["👤 Профиль", "⚙️Настройки"]]
    reply_markup = ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True)
    kb = [
        [InlineKeyboardButton("💎 Купить Premium", callback_data="buy_premium_info")]
    ]
    await context.bot.send_message(
        user_id,
        text,
        reply_markup=reply_markup,
        parse_mode="HTML"
    )
    await context.bot.send_message(
        user_id,
        "Хотите больше возможностей? Получите Premium 👑 и получите больше токенов, бонусов и приоритетный доступ!",
        reply_markup=InlineKeyboardMarkup(kb)
    )

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    args = context.args
    referred_by = None
    if args and args[0].startswith("ref"):
        referred_by_code = args[0]
        referred = execute_db("SELECT user_id FROM referrals WHERE referral_code = ?", (referred_by_code,), fetchone=True)
        if referred and referred[0] != user_id:
            referred_by = referred[0]
            set_user_referred_by(user_id, referred_by)
            add_ref_count(referred_by, 1)
            referrer = get_user_data(referred_by)
            if referrer:
                bonus = LIMITS["premium_plus" if referrer.get("premium_plus") else "premium" if referrer.get("premium") else "free"]["ref_bonus"]
                add_user_tokens(referred_by, bonus)
    if not get_user_data(user_id):
        now = datetime.datetime.now()
        user = {
            "tokens": LIMITS["free"]["tokens"],
            "words": 0,
            "premium": False,
            "premium_plus": False,
            "expires_at": None,
            "last_reset": now,
            "model": "chatgpt_4_1_nano",
            "referred_by": referred_by,
            "ref_count": 0,
            "last_message_time": 0,
            "last_active_date": now,
        }
        update_user_data(user_id, user)
    reply_keyboard = [["👤 Профиль", "⚙️Настройки"]]
    reply_markup = ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True)
    subscribed = await check_subscription(user_id, context)
    if subscribed:
        await update.message.reply_text(
            "🌟 Добро пожаловать в умного Telegram-бота!\n\n"
            "Используйте разные модели ИИ для общения и генерации изображений. "
            "Заходите в настройки, чтобы выбрать нужную модель или узнать о бонусах!\n\n"
            "❗️ Для получения большего количества токенов приглашайте друзей или выполняйте задания.\n"
            "Если возникнут вопросы или проблемы — пишите в поддержку: @ggselton 📩",
            reply_markup=reply_markup
        )
    else:
        subscribe_buttons = [
            [InlineKeyboardButton("📢 Подписаться №1", url=f"https://t.me/{CHANNEL_IDS[0][1:]}")],
            [InlineKeyboardButton("📢 Подписаться №2", url=f"https://t.me/{CHANNEL_IDS[1][1:]}")],
            [InlineKeyboardButton("✅ Проверить подписки", callback_data="check_subscription")]
        ]
        text = (
            "🎉 Добро пожаловать!\n"
            "Чтобы пользоваться ботом, подпишитесь на основные каналы:\n\n"
            f"📢 [Канал №1](https://t.me/{CHANNEL_IDS[0][1:]})\n"
            f"📢 [Канал №2](https://t.me/{CHANNEL_IDS[1][1:]})\n\n"
            "После подписки нажмите «Проверить подписки» ✅."
        )
        await update.message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup(subscribe_buttons),
            parse_mode="Markdown"
        )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    user_data = get_user_data(user_id)

    if query.data == "check_subscription":
        if not await check_subscription(user_id, context):
            subscribe_buttons = [
                [InlineKeyboardButton("📢 Подписаться №1", url=f"https://t.me/{CHANNEL_IDS[0][1:]}")],
                [InlineKeyboardButton("📢 Подписаться №2", url=f"https://t.me/{CHANNEL_IDS[1][1:]}")],
                [InlineKeyboardButton("✅ Проверить подписки", callback_data="check_subscription")]
            ]
            await query.edit_message_text(
                "❗ Вы не подписаны на все основные каналы. Подпишитесь и повторите попытку.",
                reply_markup=InlineKeyboardMarkup(subscribe_buttons),
            )
        else:
            await query.delete_message()
            await profile(update, context)

    elif query.data == "buy_premium_info":
        text = (
            "💎 <b>Покупка Premium или Premium+</b> 💎\n\n"
            "1️⃣ Выберите вид подписки и нажмите кнопку оплаты через DonationAlerts\n"
            "2️⃣ Оплатите выбранную подписку\n\n"
            "<b>Преимущества подписок:</b>\n"
            "• <b>Premium:</b> 300 токенов каждый день, увеличенные бонусы за друзей и задания, приоритетный доступ\n"
            "• <b>Premium+:</b> 500 токенов каждый день, максимальные бонусы и эксклюзивные возможности\n\n"
            "После оплаты Premium или Premium+ ваш аккаунт будет активирован автоматически (через API/вебхук).\n"
            "Если возникнут вопросы или проблемы — пишите в техподдержку: @ggselton 📩"
        )
        kb = [
            [
                InlineKeyboardButton("💎 Купить Premium (месяц)", url=DONATIONALERTS_PREMIUM_LINK)
            ],
            [
                InlineKeyboardButton("👑 Купить Premium+ (месяц)", url=DONATIONALERTS_PREMIUM_PLUS_LINK)
            ]
        ]
        await query.message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup(kb),
            parse_mode="HTML"
        )

    elif query.data == "choose_text_model_menu":
        await query.message.delete()
        model_buttons, _ = get_model_buttons(get_user_data(user_id).get("model"))
        model_buttons.append([InlineKeyboardButton("🔙 Назад", callback_data="settings_menu")])
        await context.bot.send_message(user_id, "🤖 <b>Выберите текстовую модель ИИ:</b>", reply_markup=InlineKeyboardMarkup(model_buttons), parse_mode="HTML")

    elif query.data == "choose_image_model_menu":
        await query.message.delete()
        _, img_buttons = get_model_buttons(get_user_data(user_id).get("model"))
        img_buttons.append([InlineKeyboardButton("🔙 Назад", callback_data="settings_menu")])
        await context.bot.send_message(user_id, "🖼️ <b>Выберите модель генерации изображений:</b>", reply_markup=InlineKeyboardMarkup(img_buttons), parse_mode="HTML")

    elif query.data == "settings_menu":
        await query.message.delete()
        kb = get_settings_menu()
        await context.bot.send_message(user_id, 
            "⚙️ <b>Меню настроек:</b>\n\n"
            "• Здесь вы можете выбрать нужную модель ИИ, узнать о бонусах и заданиях, а также вернуться к своему профилю.\n"
            "• Премиум-аккаунт даёт больше токенов и расширяет ваши возможности!",
            reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")

    elif query.data.startswith("choose_model_"):
        model_key = query.data[len("choose_model_"):]
        if model_key not in AI_MODELS:
            await query.message.reply_text("❌ Модель не найдена.")
            return
        user_data["model"] = model_key
        update_user_data(user_id, user_data)
        await query.message.delete()
        model = AI_MODELS[model_key]
        kb = [
            [
                InlineKeyboardButton(
                    f"💎 Выбрать {model['title']} за {model['price']} ток.",
                    callback_data=f"use_model_{model_key}"
                )
            ],
            [
                InlineKeyboardButton("🔙 Назад", callback_data="choose_text_model_menu" if model["type"] == "text" else "choose_image_model_menu")
            ]
        ]
        await context.bot.send_message(user_id, f"🤖 <b>{model['title']}</b>\n\nЦена за 1 запрос: <b>{model['price']} токенов</b>.\nНажмите кнопку ниже для выбора.", reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")

    elif query.data.startswith("use_model_"):
        model_key = query.data[len("use_model_"):]
        if model_key not in AI_MODELS:
            await query.message.reply_text("❌ Модель не найдена.")
            return
        user_data["model"] = model_key
        update_user_data(user_id, user_data)
        await query.message.delete()
        await context.bot.send_message(user_id, f"🤖 <b>Модель {AI_MODELS[model_key]['title']}</b> установлена!\nТеперь ваши запросы будут выполняться с помощью этой модели.", parse_mode="HTML")
        await profile(update, context)

    elif query.data == "bonuses_info":
        await query.message.delete()
        kb = [
            [InlineKeyboardButton("👥 Пригласить друга", callback_data="referral_info")],
            [InlineKeyboardButton("🎯 Задания", callback_data="quests_info")],
            [InlineKeyboardButton("🔙 Назад", callback_data="settings_menu")]
        ]
        await context.bot.send_message(user_id, (
            "🎁 <b>Бонусы и задания</b>\n\n"
            "• Получайте дополнительные токены за приглашение друзей или выполнение простых заданий — подписки на дополнительные каналы.\n"
            "• Выберите нужный раздел ниже 👇"),
            parse_mode="HTML", reply_markup=InlineKeyboardMarkup(kb))

    elif query.data == "referral_info":
        await query.message.delete()
        referral_code = get_or_create_referral_code(user_id)
        user_data = get_user_data(user_id)
        ref_bonus = LIMITS["premium_plus" if user_data.get("premium_plus") else "premium" if user_data.get("premium") else "free"]["ref_bonus"]
        premium = user_data.get("premium_plus") or user_data.get("premium")
        text = (
            "👥 <b>Пригласите друга!</b>\n\n"
            "• Поделитесь личной реферальной ссылкой и получите <b>{}</b> токенов за каждого друга!\n"
            "• Ваш режим: <b>{}</b>\n\n"
            "Ваша реферальная ссылка:\n"
            "<code>https://t.me/{botname}?start={ref}</code>\n\n"
            "<i>Чем больше друзей — тем больше токенов!</i>\n"
        ).format(ref_bonus, "Premium+" if user_data.get("premium_plus") else ("Premium" if user_data.get("premium") else "Базовый"), botname=context.bot.username, ref=referral_code)
        kb = [[InlineKeyboardButton("🔙 Назад", callback_data="bonuses_info")]]
        await context.bot.send_message(user_id, text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(kb))

    elif query.data == "quests_info":
        await query.message.delete()
        quest_channels = get_quest_channels()
        kb = []
        for ch_url, bonus in quest_channels:
            kb.append([InlineKeyboardButton("Подписаться", url=ch_url), InlineKeyboardButton("Проверить", callback_data=f"quest_check_{ch_url}")])
        kb.append([InlineKeyboardButton("🔙 Назад", callback_data="bonuses_info")])
        await context.bot.send_message(
            user_id,
            "🎯 <b>Задания</b>\n\n"
            "• Подпишитесь на любой из каналов ниже и получите токены! "
            "Нажмите «Проверить» после подписки.\n"
            "• За некоторые задания даём <b>15</b> токенов.\n",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(kb))

    elif query.data.startswith("quest_check_"):
        channel_url = query.data[len("quest_check_"):]
        quest_channels = dict(get_quest_channels())
        bonus = quest_channels.get(channel_url, 15)
        if quest_already_claimed(user_id, channel_url):
            await query.message.reply_text("✅ Вы уже получили бонус за этот канал.")
            return
        if await check_quest_subscription(user_id, context, channel_url):
            set_quest_claimed(user_id, channel_url)
            add_user_tokens(user_id, bonus)
            await query.message.reply_text(f"🎉 Подписка подтверждена! Вам начислено <b>{bonus}</b> токенов.", parse_mode="HTML")
        else:
            await query.message.reply_text("❗️ Вы не подписаны на этот канал. Подпишитесь и повторите попытку.")

    elif query.data == "back_to_profile":
        await query.message.delete()
        await profile(update, context)

async def ai_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg or not msg.from_user or (msg.chat and msg.chat.type == "channel"):
        return
    user_id = msg.from_user.id
    if not await check_subscription(user_id, context):
        await msg.reply_text("❌ Для использования бота необходимо подписаться на все основные каналы.")
        return
    data = get_user_data(user_id)
    if not data:
        await msg.reply_text("❌ Ошибка. Пользователь не найден.")
        return
    is_premium = data.get("premium", False)
    is_premium_plus = data.get("premium_plus", False)
    tokens = data.get("tokens", 0)
    model_key = data.get("model", "chatgpt_4_1_nano")
    if model_key not in AI_MODELS:
        model_key = "chatgpt_4_1_nano"
    model = AI_MODELS[model_key]
    price = model["price"]
    word_count = len(msg.text.split())
    limit_type = "premium_plus" if is_premium_plus else "premium" if is_premium else "free"
    if word_count > LIMITS[limit_type]["word_limit"]:
        await msg.reply_text(f"❌ Максимальное количество слов в запросе — {LIMITS[limit_type]['word_limit']}.")
        return
    if tokens < price:
        await msg.reply_text(f"❌ Недостаточно токенов! Пополните баланс через приглашения или задания.")
        return

    context_history = user_context[user_id]
    context_history.append({"role": "user", "content": msg.text})
    if len(context_history) > 10:
        context_history[:] = context_history[-10:]

    data["tokens"] -= price
    data["words"] += word_count
    data["last_message_time"] = int(time.time())
    data["last_active_date"] = datetime.datetime.now()
    update_user_data(user_id, data)
    thinking_msg = await msg.reply_text("🧠 Думаю...")

    try:
        if model_key == "dall_e":
            headers = {
                "Authorization": f"Bearer {model['api_key']}",
                "Content-Type": "application/json",
            }
            payload = {
                "prompt": msg.text,
                "n": 1,
                "size": "1024x1024"
            }
            r = requests.post(model["api_url"], headers=headers, json=payload, timeout=60)
            r.raise_for_status()
            response_data = r.json()
            image_url = response_data.get("data", [{}])[0].get("url")
            await thinking_msg.delete()
            if image_url:
                await msg.reply_photo(image_url, caption="🖼️ Ваше сгенерированное изображение!")
            else:
                await msg.reply_text("⚠️ Не удалось сгенерировать изображение.")
            user_context[user_id] = []
            return
        else:
            headers = {
                "Authorization": f"Bearer {model['api_key']}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": model["model_id"],
                "messages": context_history,
            }
            r = requests.post(model["api_url"], headers=headers, json=payload, timeout=60)
            r.raise_for_status()
            response_data = r.json()
            response = response_data["choices"][0]["message"]["content"].strip()
            context_history.append({"role": "assistant", "content": response})
    except Exception as e:
        logging.error(f"Ошибка при обращении к ИИ: {e}")
        response = "⚠️ Ошибка при обращении к ИИ."
    await thinking_msg.delete()
    await msg.reply_text(response)

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logging.error(msg="Exception while handling an update:", exc_info=context.error)
    if (
        update
        and hasattr(update, "effective_message")
        and update.effective_message
        and hasattr(update.effective_message, "chat")
        and update.effective_message.chat.type in ("private", "group", "supergroup")
    ):
        try:
            await update.effective_message.reply_text("❌ Произошла ошибка, попробуйте позже.")
        except Exception:
            pass

async def keyboard_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "👤 Профиль":
        await profile(update, context)
    elif text == "⚙️Настройки":
        kb = get_settings_menu()
        await context.bot.send_message(
            update.effective_user.id,
            "⚙️ <b>Меню настроек:</b>\n\n"
            "— Управляйте своим профилем, выбирайте модели, открывайте бонусы и задания.\n"
            "— Премиум-аккаунт расширяет ваши возможности!",
            reply_markup=InlineKeyboardMarkup(kb),
            parse_mode="HTML"
        )

def parse_time(timestr):
    parts = timestr.split(":")
    if len(parts) == 2:
        return datetime.time(int(parts[0]), int(parts[1]))
    elif len(parts) == 3:
        return datetime.time(int(parts[0]), int(parts[1]), int(parts[2]))
    else:
        raise ValueError("Неподдерживаемый формат времени")

async def add_ad(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("❌ У вас нет прав для этой команды.")
        return
    if len(context.args) < 3:
        await update.message.reply_text(
            "❌ Неверный формат команды. Используйте: /add HH:MM DD.MM.YYYY-DD.MM.YYYY https://t.me/channel/POST_ID"
        )
        return
    time_to_send = context.args[0]
    date_range = context.args[1]
    post_url = context.args[2] if len(context.args) == 3 else " ".join(context.args[2:])
    try:
        start_str, end_str = date_range.split("-")
        start_date = datetime.datetime.strptime(start_str, "%d.%m.%Y")
        end_date = datetime.datetime.strptime(end_str, "%d.%m.%Y")
        send_time = time_to_send.strip()
        try:
            datetime.datetime.strptime(send_time, "%H:%M")
        except Exception:
            await update.message.reply_text("❌ Время должно быть в формате HH:MM")
            return
        if (end_date - start_date).days > 30:
            raise ValueError("Максимальная длительность рекламы — 1 месяц.")
    except ValueError as e:
        await update.message.reply_text(f"❌ Ошибка в дате или времени: {e}")
        return
    if not post_url.startswith("https://t.me/"):
        await update.message.reply_text("❌ Неверный формат ссылки на пост.")
        return
    parts = post_url.rstrip("/").split("/")
    if len(parts) < 5:
        await update.message.reply_text("❌ Не удалось извлечь ID канала или поста из ссылки.")
        return
    channel_username = parts[3]
    if f"@{channel_username}" != AD_CHANNEL_ID:
        await update.message.reply_text("❌ Ссылка должна вести на сообщение в рекламном канале.")
        return
    execute_db("""
        INSERT OR REPLACE INTO ads (post_url, send_time, start_date, end_date, enabled)
        VALUES (?, ?, ?, ?, 1)
    """, (
        post_url,
        send_time,
        start_date.strftime("%Y-%m-%d"),
        end_date.strftime("%Y-%m-%d")
    ), commit=True)
    await update.message.reply_text("✅ Рекламная кампания успешно добавлена!")

async def addstat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("❌ У вас нет прав.")
        return
    ads = execute_db("SELECT post_url, start_date, end_date, send_time, enabled FROM ads ORDER BY id DESC", fetchone=False)
    if not ads:
        await update.message.reply_text("Нет активных реклам.")
        return
    msg = "Активные рекламы:\n"
    for ad in ads:
        msg += f"• {'✅' if ad[4] else '❌'} {ad[0]} ({ad[1]} — {ad[2]}) | Время публикации: {ad[3]}\n"
    await update.message.reply_text(msg)

async def adddelete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("❌ У вас нет прав.")
        return
    if not context.args:
        await update.message.reply_text("Используйте: /adddelete <ссылка_на_пост>")
        return
    post_url = context.args[0]
    ad = execute_db("SELECT enabled FROM ads WHERE post_url = ?", (post_url,), fetchone=True)
    if not ad:
        await update.message.reply_text("❌Такой рекламы нет.")
        return
    if not ad[0]:
        await update.message.reply_text("Этот пост уже удалён из рекламы.")
        return
    execute_db("UPDATE ads SET enabled = 0 WHERE post_url = ?", (post_url,), commit=True)
    await update.message.reply_text("❌Реклама успешно отключена и больше не будет показываться.")

async def stat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("❌ У вас нет прав.")
        return
    total = execute_db("SELECT COUNT(*) FROM users", fetchone=True)[0]
    premium = execute_db("SELECT COUNT(*) FROM users WHERE premium = 1 AND expires_at > ?", (datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),), fetchone=True)[0]
    last_day = execute_db("SELECT COUNT(*) FROM users WHERE last_active_date >= date('now', '-1 day')", fetchone=True)[0]
    last_month = execute_db("SELECT COUNT(*) FROM users WHERE last_active_date >= date('now', '-30 day')", fetchone=True)[0]
    execute_db("INSERT OR REPLACE INTO stat (key, value) VALUES (?, ?)", ("total", total), commit=True)
    execute_db("INSERT OR REPLACE INTO stat (key, value) VALUES (?, ?)", ("premium", premium), commit=True)
    execute_db("INSERT OR REPLACE INTO stat (key, value) VALUES (?, ?)", ("last_day", last_day), commit=True)
    execute_db("INSERT OR REPLACE INTO stat (key, value) VALUES (?, ?)", ("last_month", last_month), commit=True)
    await update.message.reply_text(f"Пользователи: {total}/{premium}/{last_day}/{last_month}")

async def send_advertisements(context: ContextTypes.DEFAULT_TYPE):
    now = datetime.datetime.now()
    current_time = now.time()
    current_date = now.date()
    today_str = current_date.strftime("%Y-%m-%d")
    ads = execute_db("""
        SELECT id, post_url, send_time, start_date, end_date, total_shows, enabled, last_sent_date
        FROM ads 
        WHERE start_date <= ? AND end_date >= ? AND enabled = 1
    """, (today_str, today_str), fetchone=False)
    for ad in ads:
        ad_id, post_url, send_time, start_date, end_date, total_shows, enabled, last_sent_date = ad
        try:
            scheduled_time = parse_time(send_time)
        except Exception as e:
            logging.error(f"Ошибка разбора времени рекламы: {send_time} -- {e}")
            continue
        if (current_time.hour == scheduled_time.hour
            and current_time.minute == scheduled_time.minute
            and (not last_sent_date or last_sent_date != today_str)):
            parts = post_url.rstrip("/").split("/")
            if len(parts) < 5:
                continue
            channel_username = parts[3]
            message_id = int(parts[4])
            if not channel_username.startswith("@"):
                channel_username = "@" + channel_username
            users = execute_db("SELECT user_id FROM users", fetchone=False)
            for user in users:
                user_id = user[0]
                try:
                    await context.bot.copy_message(
                        chat_id=user_id,
                        from_chat_id=channel_username,
                        message_id=message_id
                    )
                    execute_db("UPDATE ads SET total_shows = total_shows + 1 WHERE id = ?", (ad_id,), commit=True)
                except Exception as e:
                    logging.error(f"Ошибка при отправке рекламы пользователю {user_id}: {e}")
            execute_db("UPDATE ads SET last_sent_date = ? WHERE id = ?", (today_str, ad_id), commit=True)

async def adc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("❌ У вас нет прав.")
        return
    if not context.args:
        await update.message.reply_text("Пример использования: /adc https://t.me/yourchannel")
        return
    ch_url = context.args[0]
    bonus = int(context.args[1]) if len(context.args) > 1 and str(context.args[1]).isdigit() else 15
    if not ch_url.startswith("https://t.me/"):
        await update.message.reply_text("Введите ссылку на канал в формате https://t.me/name")
        return
    add_quest_channel(ch_url, bonus)
    await update.message.reply_text(f"Канал {ch_url} добавлен в задания с бонусом {bonus}!")

async def adcdelete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("❌ У вас нет прав.")
        return
    if not context.args:
        await update.message.reply_text("Пример использования: /adcdelete https://t.me/yourchannel")
        return
    ch_url = context.args[0]
    del_quest_channel(ch_url)
    await update.message.reply_text(f"Канал {ch_url} удалён из заданий.")

async def daily_token_reset(context: ContextTypes.DEFAULT_TYPE):
    now = datetime.datetime.now()
    for row in execute_db("SELECT user_id, premium, premium_plus FROM users", fetchone=False):
        user_id, premium, premium_plus = row
        data = get_user_data(user_id)
        if premium_plus:
            data["tokens"] = LIMITS["premium_plus"]["tokens"]
        elif premium:
            data["tokens"] = LIMITS["premium"]["tokens"]
        else:
            data["tokens"] = LIMITS["free"]["tokens"]
        data["last_reset"] = now
        update_user_data(user_id, data)

# --- DonationAlerts Webhook Handler ---
async def donationalerts_webhook(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Этот хендлер должен вызываться через отдельный webhook endpoint вне Telegram
    # Пример интеграции с Flask/FastAPI: в этой функции логика активации премиума по payment_id и user_id
    # Ниже пример работы с Telegram user_id, subscription_type ("premium" или "premium_plus")
    # ВАЖНО: Вызывать update_user_subscription(user_id, subscription_type) по факту успешной оплаты!
    pass  # Имплементация на стороне вашего веб-приложения (Flask/FastAPI)

def update_user_subscription(user_id: int, subscription_type: str):
    now = datetime.datetime.now()
    expires = now + datetime.timedelta(days=PREMIUM_PLUS_DAYS if subscription_type == "premium_plus" else PREMIUM_DAYS)
    data = get_user_data(user_id) or {
        "tokens": LIMITS["premium_plus" if subscription_type == "premium_plus" else "premium"]["tokens"],
        "words": 0,
        "premium": False,
        "premium_plus": False,
        "last_reset": now,
        "model": "chatgpt_4_1_nano",
        "ref_count": 0,
        "last_message_time": 0,
        "last_active_date": now,
    }
    if subscription_type == "premium_plus":
        data["premium"] = True
        data["premium_plus"] = True
        data["expires_at"] = expires
        data["tokens"] = LIMITS["premium_plus"]["tokens"]
    else:
        data["premium"] = True
        data["premium_plus"] = False
        data["expires_at"] = expires
        data["tokens"] = LIMITS["premium"]["tokens"]
    update_user_data(user_id, data)
    # Можно добавить уведомление пользователю через Telegram бот:
    # context.bot.send_message(user_id, f"✅ {subscription_type.capitalize()} активирован на месяц! Спасибо за оплату.")

def main():
    init_db()
    migrate_db()
    give_premium_to_admins()
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("profile", profile))
    application.add_handler(CommandHandler("add", add_ad))
    application.add_handler(CommandHandler("addstat", addstat))
    application.add_handler(CommandHandler("adddelete", adddelete))
    application.add_handler(CommandHandler("stat", stat))
    application.add_handler(CommandHandler("adc", adc))
    application.add_handler(CommandHandler("adcdelete", adcdelete))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.Regex(r"^👤 Профиль$") | filters.Regex(r"^⚙️Настройки$"), keyboard_handler))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), ai_message_handler))
    application.add_error_handler(error_handler)
    job_queue = application.job_queue
    job_queue.run_repeating(send_advertisements, interval=60, first=0)
    job_queue.run_repeating(daily_token_reset, interval=60*60*24, first=0)
    print("✳️Бот запущен...")
    application.run_polling()

if __name__ == "__main__":
    main()