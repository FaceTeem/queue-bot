import random
import logging
import asyncio
from datetime import date, timedelta
import config
import re

try:
    from playwright.async_api import async_playwright
except ImportError:
    async_playwright = None

log = logging.getLogger("fetcher")

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
]

def _get_random_user_agent():
    return random.choice(USER_AGENTS)

class SessionExpired(Exception):
    pass

def _demo_dates():
    items = []
    if random.random() < 0.4:
        return items
    cities_list = list(config.CITIES.keys())
    for _ in range(random.randint(1, 4)):
        d = date.today() + timedelta(days=random.randint(1, 30))
        items.append({
            "city": random.choice(cities_list),
            "service": random.choice(config.SERVICES),
            "date": d.isoformat(),
        })
    return items

async def fetch_dates(http=None):
    if config.MODE == "demo":
        return _demo_dates()
    return await _live_dates()

async def _live_dates():
    all_items = []
    try:
        import db
        await db.init()

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True, args=[
                '--disable-blink-features=AutomationControlled',
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--disable-gpu',
            ])

            subscribed_cities = set()
            for city in config.CITIES.keys():
                subs = await db.subscribers(city, config.SERVICES[0])
                if subs:
                    subscribed_cities.add(city)

            if not subscribed_cities:
                log.info("Немає підписок")
                await browser.close()
                return all_items

            log.info(f"Запити для: {', '.join(subscribed_cities)}")

            for city_ua in subscribed_cities:
                try:
                    context = await browser.new_context(
                        proxy={
                            "server": "http://brd.superproxy.io:44445",
                            "username": "brd-customer-hl_dab5cadf-zone-isp_proxy1",
                            "password": "fcpk6bf7mro1"
                        },
                        user_agent=_get_random_user_agent()
                    )
                    page = await context.new_page()
                    
                    log.info(f"{city_ua}: запит...")
                    await page.goto("https://pasport.org.ua/en/solutions/e-queue", wait_until="load", timeout=60000)
                    await page.wait_for_timeout(3000)
                    content = await page.content()

                    if len(content) > 500:
                        dates = re.findall(r'\d{4}-\d{2}-\d{2}', content)
                        if dates:
                            for service in config.SERVICES:
                                for dt in list(set(dates))[:3]:
                                    all_items.append({"city": city_ua, "service": service, "date": dt})
                            log.info(f"✅ {city_ua}: {len(set(dates))} дат ЗНАЙДЕНО!")
                        else:
                            log.info(f"⚪ {city_ua}: 0 дат (немає відкритих)")
                    else:
                        log.info(f"❌ {city_ua}: помилка завантаження")

                    await context.close()
                    await asyncio.sleep(15)

                except Exception as e:
                    log.error(f"❌ {city_ua}: {e}")
                    await asyncio.sleep(10)

            await browser.close()

    except Exception as e:
        log.error(f"Критична помилка: {e}")

    return all_items
