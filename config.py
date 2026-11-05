import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")

# Safe parsing of ADMIN_ID: if not a valid int, default to 0
try:
    admin_id_str = os.getenv("ADMIN_ID", "").strip()
    ADMIN_ID = int(admin_id_str) if admin_id_str else 0
except ValueError:
    ADMIN_ID = 0

# How often to check for slots (seconds).
# 300s (5 min) = 288 checks/day per city. Not too aggressive.
# Adjust based on site's tolerance.
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", "300"))

# "demo" = fake slots for testing the bot; "live" = real requests to SLOTS_URL
MODE = os.getenv("MODE", "demo")

# Filled in after you find the real request in DevTools (see README)
SLOTS_URL = os.getenv("SLOTS_URL", "")
SESSION_COOKIE = os.getenv("SESSION_COOKIE", "")
AUTH_HEADER = os.getenv("AUTH_HEADER", "")

DB_PATH = os.getenv("DB_PATH", "bot.db")

# Cities: Ukrainian name → URL code for pasport.org.ua
CITIES = {
    "Варшава": "warsaw",
    "Краків": "krakow",
    "Вроцлав": "wroclaw",
    "Гданськ": "gdansk",
    "Люблін": "lublin",
    "Прага": "prague",
    "Берлін": "berlin",
    "Київ": "kyiv",
    "Львів": "lviv",
    "Одеса": "odesa",
    "Дніпро": "dnipro",
    "Харків": "kharkiv",
}

# Cities available for subscription (user-facing)
# Only Polish cities for testing per-city requests
SUBSCRIBE_CITIES = ["Варшава", "Краків", "Вроцлав", "Гданськ", "Люблін", "Прага", "Берлін"]

SERVICES = ["Закордонний паспорт", "ID-картка"]
