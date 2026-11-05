import asyncio
import logging
import random
import sqlite3

from aiogram import Bot, Dispatcher, F
from aiogram.exceptions import TelegramForbiddenError
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message, ReplyKeyboardMarkup, KeyboardButton

import config
import db
from fetcher import SessionExpired, fetch_dates

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("queue-bot")

dp = Dispatcher()

def fmt_date(iso: str) -> str:
    try:
        y, m, d = iso.split("-")
        return f"{d}.{m}.{y}"
    except ValueError:
        return iso

def kb(items, prefix, cols=2):
    rows, row = [], []
    for name in items:
        row.append(InlineKeyboardButton(text=name, callback_data=f"{prefix}:{name}"))
        if len(row) == cols:
            rows.append(row); row = []
    if row:
        rows.append(row)
    return InlineKeyboardMarkup(inline_keyboard=rows)

def main_menu():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="📍 Підписатись"), KeyboardButton(text="📋 Мої підписки")],
        [KeyboardButton(text="📊 Статус"), KeyboardButton(text="🛑 Відписатись")],
        [KeyboardButton(text="❓ Допомога")]
    ], resize_keyboard=True)

@dp.message(CommandStart())
async def start(m: Message):
    try:
        with open('bot_image.png', 'rb') as img:
            await m.answer_photo(img, caption="Привіт! Я стежу за чергою ДП «Документ» 24/7.\n\nВиберіть дію:", reply_markup=main_menu())
    except FileNotFoundError:
        await m.answer("Привіт! Я стежу за чергою ДП «Документ» 24/7.\n\nВиберіть дію:", reply_markup=main_menu())

@dp.message(F.text == "📍 Підписатись")
async def subscribe(m: Message):
    await m.answer("Оберіть місто:", reply_markup=kb(config.SUBSCRIBE_CITIES, "city", cols=2))

@dp.message(F.text == "📋 Мої підписки")
async def my(m: Message):
    subs = await db.user_subs(m.from_user.id)
    if not subs:
        await m.answer("Підписок немає.\n\nКлікни '📍 Підписатись' для додавання.")
    else:
        await m.answer("Ваші підписки:\n" + "\n".join(f"• {c}, {s}" for c, s in subs))

@dp.message(F.text == "📊 Статус")
async def status(m: Message):
    mode_text = "LIVE 🔴" if config.MODE == "live" else "демо 🔵"
    await m.answer(f"Бот працює в режимі {mode_text}.\n\nВільні дати показуватимуться тут.")

@dp.message(F.text == "🛑 Відписатись")
async def stop(m: Message):
    await db.remove_all(m.from_user.id)
    await m.answer("Усі підписки видалено.")

@dp.message(F.text == "❓ Допомога")
async def help_cmd(m: Message):
    await m.answer("ℹ️ ПРО БОТ:\nTelegram-бот для моніторингу черги ДП «Документ».\nСтежимо за датами 24/7 і надсилаємо сповіщення!\n\n❓ FAQ:\n• Як підписатися?\n  → Клікни '📍 Підписатись' і виберіть місто\n\n• Коли прийде сповіщення?\n  → Коли дата відкриється в обраному місті\n\n• Як побачити мої підписки?\n  → Клікни '📋 Мої підписки'\n\n• Як відписатися?\n  → Клікни '🛑 Відписатись'")

@dp.callback_query(F.data.startswith("city:"))
async def pick_city(c: CallbackQuery):
    city = c.data.split(":", 1)[1]
    markup = kb([s for s in config.SERVICES], f"svc:{city}", cols=1)
    await c.message.edit_text(f"{city} — яка послуга?", reply_markup=markup)

@dp.callback_query(F.data.startswith("svc:"))
async def pick_service(c: CallbackQuery):
    parts = c.data.split(":", 1)
    city, service = parts[1].rsplit(":", 1)
    await db.add_sub(c.from_user.id, city, service)
    await c.message.edit_text(f"✅ Підписка: {city}, {service}.")

@dp.message(Command("admin_broadcast"))
async def admin_broadcast(m: Message):
    if config.ADMIN_ID and m.from_user.id != config.ADMIN_ID:
        return
    text = m.text.replace('/admin_broadcast', '').strip()
    if not text:
        await m.answer('Синтаксис: /admin_broadcast текст')
        return
    conn = sqlite3.connect(config.DB_PATH)
    cur = conn.cursor()
    cur.execute('SELECT DISTINCT user_id FROM subs')
    users = [row[0] for row in cur.fetchall()]
    conn.close()
    sent = 0
    for uid in users:
        try:
            await m.bot.send_message(uid, f'{text}')
            sent += 1
            await asyncio.sleep(0.05)
        except:
            pass
    await m.answer(f'✅ Надіслано {sent} користувачам')

async def checker(bot: Bot):
    expired_notified = False
    errors = 0
    while True:
        try:
            items = await fetch_dates()
            errors, expired_notified = 0, False
            log.info("checked: %d open dates", len(items))

            new_dates: dict[tuple, set] = {}
            for s in items:
                city, service, date = s["city"], s["service"], s["date"]
                subs = await db.subscribers(city, service)
                if not subs:
                    continue
                key = f"{city}|{service}|{date}"
                if await db.is_new(key):
                    new_dates.setdefault((city, service), set()).add(date)

            for (city, service), dates in new_dates.items():
                dates_txt = "\n".join(f"• {fmt_date(d)}" for d in sorted(dates))
                text = (f"Відкрилась черга!\n{city}\n{service}\n\nВільні дати:\n{dates_txt}")
                for uid in await db.subscribers(city, service):
                    try:
                        await bot.send_message(uid, text)
                        await asyncio.sleep(0.05)
                    except TelegramForbiddenError:
                        log.info("user %s blocked bot", uid)
                        await db.remove_all(uid)
                    except Exception as e:
                        log.warning("send failed: %s", e)
        except SessionExpired as e:
            log.error("session expired: %s", e)
            if config.ADMIN_ID and not expired_notified:
                await bot.send_message(config.ADMIN_ID, "Сесія закінчилась.")
                expired_notified = True
        except Exception as e:
            errors += 1
            log.error("check failed (%d): %s", errors, e)

        jitter = random.randint(30, 90)
        backoff = config.CHECK_INTERVAL * min(2 ** errors, 8) if errors > 0 else config.CHECK_INTERVAL
        delay = backoff + jitter
        await asyncio.sleep(delay)

async def main():
    if not config.BOT_TOKEN:
        raise SystemExit("BOT_TOKEN потрібна!")
    bot = Bot(config.BOT_TOKEN)
    await db.init()
    asyncio.create_task(checker(bot))
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
