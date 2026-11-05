import asyncio
import logging
import random

from aiogram import Bot, Dispatcher, F
from aiogram.exceptions import TelegramForbiddenError
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

import config
import db
from fetcher import SessionExpired, fetch_dates

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("queue-bot")

dp = Dispatcher()


def fmt_date(iso: str) -> str:
    """2026-11-20 -> 20.11.2026"""
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


@dp.message(CommandStart())
async def start(m: Message):
    try:
        # Send image with greeting
        with open('bot_image.png', 'rb') as img:
            await m.answer_photo(
                img,
                caption="Привіт! Я стежу за чергою ДП «Документ» і пишу, щойно вона відкривається.\n\n"
                        "Команди:\n"
                        "/subscribe — підписатися на місто\n"
                        "/my — мої підписки\n"
                        "/status — поточний стан\n"
                        "/stop — відписатися від усього\n\n"
                        "Я лише сповіщаю. Записуватися треба самостійно на офіційному сайті."
            )
    except FileNotFoundError:
        # Fallback if image not found
        await m.answer(
            "Привіт! Я стежу за чергою ДП «Документ» і пишу, щойно вона відкривається, з вільними датами.\n\n"
            "Команди:\n"
            "/subscribe — підписатися на місто\n"
            "/my — мої підписки\n"
            "/status — поточний стан\n"
            "/stop — відписатися від усього\n\n"
            "Я лише сповіщаю. Записуватися треба самостійно на офіційному сайті Паспортного сервісу."
        )


@dp.message(Command("subscribe"))
async def subscribe(m: Message):
    await m.answer("Оберіть місто:", reply_markup=kb(config.SUBSCRIBE_CITIES, "city", cols=2))


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
    await c.message.edit_text(f"✅ Підписка: {city}, {service}. Напишу, щойно відкриється черга.")


@dp.message(Command("my"))
async def my(m: Message):
    subs = await db.user_subs(m.from_user.id)
    if not subs:
        await m.answer("Підписок немає. /subscribe")
        return
    await m.answer("Ваші підписки:\n" + "\n".join(f"• {c}, {s}" for c, s in subs))


@dp.message(Command("stop"))
async def stop(m: Message):
    await db.remove_all(m.from_user.id)
    await m.answer("Усі підписки видалено.")


@dp.message(Command("status"))
async def status(m: Message):
    mode_text = "LIVE 🔴" if config.MODE == "live" else "демо 🔵"
    await m.answer(f"Бот працює в режимі {mode_text}. Вільні дати показуватимуться тут.")


async def checker(bot: Bot):
    """Background loop: fetch slots, alert subscribers about new ones."""
    expired_notified = False
    errors = 0
    while True:
        try:
            items = await fetch_dates()
            errors, expired_notified = 0, False
            log.info("checked: %d open dates", len(items))

            # group new dates by city + service -> one message per queue
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
                text = (f"🟢 Відкрилась черга!\n📍 {city}\n📄 {service}\n\n"
                        f"Вільні дати:\n{dates_txt}\n\nЗаписуйтесь на сайті Паспортного сервісу.")
                for uid in await db.subscribers(city, service):
                    try:
                        await bot.send_message(uid, text)
                        await asyncio.sleep(0.05)  # Telegram limit ~30 msg/s
                    except TelegramForbiddenError:
                        log.info("user %s blocked bot, removing", uid)
                        await db.remove_all(uid)
                    except Exception as e:
                        log.warning("send to %s failed: %s", uid, e)
        except SessionExpired as e:
            log.error("session expired: %s", e)
            if config.ADMIN_ID and not expired_notified:
                await bot.send_message(config.ADMIN_ID, "⚠️ Сесія на сайті закінчилась. Оновіть SESSION_COOKIE у .env і перезапустіть бота.")
                expired_notified = True
        except Exception as e:
            errors += 1
            log.error("check failed (%d): %s", errors, e)

        # jitter (30-90s) + back off on repeated errors, so we don't look like a bot
        # Even on success, add jitter to avoid predictable patterns
        jitter = random.randint(30, 90)
        backoff = config.CHECK_INTERVAL * min(2 ** errors, 8) if errors > 0 else config.CHECK_INTERVAL
        delay = backoff + jitter
        log.debug(f"Next check in {delay}s (interval: {backoff}s, jitter: {jitter}s, errors: {errors})")
        await asyncio.sleep(delay)


@dp.message(Command("admin_stats"))
async def admin_stats(m: Message):
    if config.ADMIN_ID and m.from_user.id != config.ADMIN_ID:
        return
    import sqlite3
    conn = sqlite3.connect(config.DB_PATH)
    cur = conn.cursor()
    cur.execute('SELECT COUNT(DISTINCT user_id) FROM subs')
    row = cur.fetchone()
    users = row[0] if row else 0
    cur.execute('SELECT COUNT(*) FROM subs')
    row = cur.fetchone()
    subs = row[0] if row else 0
    conn.close()
    await m.answer(f"📊 Користувачів: {users}\n📍 Підписок: {subs}")


@dp.message(Command("admin_broadcast"))
async def admin_broadcast(m: Message):
    if config.ADMIN_ID and m.from_user.id != config.ADMIN_ID:
        return
    text = m.text.replace('/admin_broadcast', '').strip()
    if not text:
        await m.answer('Синтаксис: /admin_broadcast текст')
        return
    import sqlite3
    conn = sqlite3.connect(config.DB_PATH)
    cur = conn.cursor()
    cur.execute('SELECT DISTINCT user_id FROM subs')
    users = [row[0] for row in cur.fetchall()]
    conn.close()
    sent = 0
    for uid in users:
        try:
            await m.bot.send_message(uid, f'📢 {text}')
            sent += 1
        except:
            pass
    await m.answer(f'✅ Надіслано {sent} користувачам')


@dp.message(Command("admin_logs"))
async def admin_logs(m: Message):
    if config.ADMIN_ID and m.from_user.id != config.ADMIN_ID:
        return
    try:
        with open('/home/ec2-user/bot.log', 'r') as f:
            lines = f.readlines()[-30:]
            text = ''.join(lines)[-2000:]
            await m.answer(f'📋 Логи:\n\n{text}')
    except Exception as e:
        await m.answer(f'Помилка: {e}')


async def main():
    if not config.BOT_TOKEN:
        raise SystemExit("Додайте BOT_TOKEN у файл .env")
    bot = Bot(config.BOT_TOKEN)
    await db.init()
    asyncio.create_task(checker(bot))
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
