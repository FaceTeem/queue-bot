import random
import logging
import asyncio
from datetime import date, timedelta
import config

try:
    from playwright.async_api import async_playwright
except ImportError:
    async_playwright = None

try:
    import cloudscraper
except ImportError:
    cloudscraper = None

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

def _read_browser_cache():
    """Читає дані з браузер-daemon"""
    try:
        import json
        with open('/home/ec2-user/browser_cache.json', 'r', encoding='utf-8') as f:
            data = json.load(f)

        content = data.get('content', '')
        if data.get('status') == 'success' and len(content) > 500:
            import re
            dates = re.findall(r'(\d{4}-\d{2}-\d{2})', content)
            items = []
            for dt in list(set(dates))[:10]:
                items.append({
                    "city": "Варшава",
                    "service": "Закордонний паспорт",
                    "date": dt,
                })
            if items:
                log.info(f"✅ Прочитано {len(items)} дат з браузер-кешу")
                return items
    except Exception as e:
        log.warning(f"Не можу прочитати браузер-кеш: {e}")

    return []

async def _live_dates():
    """Fetch dates via Bright Data proxy - only for subscribed cities"""
    all_items = []
    import re
    import db as db_module

    try:
        await db_module.init()

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True, args=[
                '--disable-blink-features=AutomationControlled',
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--disable-gpu',
            ])

            subscribed_cities = set()
            for city in config.CITIES.keys():
                subs = await db_module.subscribers(city, config.SERVICES[0])
                if subs:
                    subscribed_cities.add(city)

            if not subscribed_cities:
                log.info("⚪ Немає підписків - запити не робляться")
                await browser.close()
                return all_items

            log.info(f"🔍 Запити для {len(subscribed_cities)} міст зі підписками: {', '.join(subscribed_cities)}")

            for city_ua in subscribed_cities:
                try:
                    context = await browser.new_context(
                        proxy={
                            "server": "http://brd.superproxy.io:44445",
                            "username": "brd-customer-h1_dab5cadf-zone-isp_proxy1",
                            "password": "fcpk6bI7mro1"
                        },
                        user_agent=_get_random_user_agent()
                    )
                    page = await context.new_page()

                    url = f"https://pasport.org.ua/en/solutions/e-queue"
                    log.info(f"📍 Запит для {city_ua}...")
                    await page.goto(url, wait_until="networkidle", timeout=60000)
                    await page.wait_for_timeout(3000)
                    content = await page.content()

                    if len(content) > 500 and "blocked" not in content.lower():
                        dates = re.findall(r'(\d{4}-\d{2}-\d{2})', content)
                        if dates:
                            for service in config.SERVICES:
                                for dt in list(set(dates))[:3]:
                                    all_items.append({
                                        "city": city_ua,
                                        "service": service,
                                        "date": dt,
                                    })
                            log.info(f"✅ {city_ua}: знайшов {len(set(dates))} дат")
                        else:
                            log.debug(f"⚪ {city_ua}: дат не знайдено")
                    else:
                        log.warning(f"❌ {city_ua}: блоковано або помало контенту")

                    await context.close()
                    await asyncio.sleep(15)

                except Exception as e:
                    log.error(f"❌ {city_ua}: {type(e).__name__}: {e}")
                    await asyncio.sleep(10)

            await browser.close()

    except Exception as e:
        log.error(f"❌ Критична помилка fetch: {type(e).__name__}: {e}")

    return all_items
