import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")

try:
    admin_id_str = os.getenv("ADMIN_ID", "").strip()
    ADMIN_ID = int(admin_id_str) if admin_id_str else 0
except ValueError:
    ADMIN_ID = 0

CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", "300"))

MODE = os.getenv("MODE", "demo")

SLOTS_URL = os.getenv("SLOTS_URL", "")
SESSION_COOKIE = os.getenv("SESSION_COOKIE", "")
AUTH_HEADER = os.getenv("AUTH_HEADER", "")

DB_PATH = os.getenv("DB_PATH", "bot.db")

CITIES = {
    "Варшава": "warsaw",
    "Краків": "krakow",
    "Вроцлав": "wroclaw",
    "Гданськ": "gdansk",
    "Прага": "prague",
    "Берлін": "berlin",
    "Київ": "kyiv",
    "Львів": "lviv",
    "Одеса": "odesa",
    "Дніпро": "dnipro",
    "Харків": "kharkiv",
}

SUBSCRIBE_CITIES = ["Варшава", "Краків", "Вроцлав", "Гданськ", "Прага", "Берлін"]

SERVICES = ["Закордонний паспорт", "ID-картка"]
