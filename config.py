"""
Конфигурация бота
"""
import os
from dotenv import load_dotenv

load_dotenv()

# Токен бота и идентификаторы
BOT_TOKEN = os.getenv("BOT_TOKEN", "8728834821:AAG1itHgw9QFZyIzhMPT4nIBiH1joBLC9CY")
ADMIN_ID = int(os.getenv("ADMIN_ID", "8641877865"))  # Замените на ваш ID
CHANNEL_ID = os.getenv("CHANNEL_ID", "-1003864000969")  # ID или @username канала
CHANNEL_LINK = os.getenv("CHANNEL_LINK", "https://t.me/kszoskskak")  # Ссылка для подписки

# Настройки базы данных
DATABASE_PATH = os.getenv("DATABASE_PATH", "data/bot_database.db")

# Настройки расписания
WORK_DAYS = list(range(7))  # Пн=0, Вс=6
WORK_HOURS = list(range(9, 20))  # Рабочие часы: 9:00 - 19:00
SLOT_DURATION = 60  # Длительность слота в минутах

# Настройки напоминаний
REMINDER_HOURS_BEFORE = 24  # За сколько часов напоминать

# Валидация конфигурации
if BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
    raise ValueError("❗ Укажите BOT_TOKEN в config.py или в .env файле")