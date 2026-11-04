import random
import logging
import asyncio
from datetime import date, timedelta
import config

try:
    from playwright.async_api import async_playwright
except ImportError:
    async_playwright = None

log = logging.getLogger("fetcher")

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
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
    if not async_playwright:
        raise Exception("Playwright not installed")

    all_items = []
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True, args=['--disable-blink-features=AutomationControlled'])
            page = await browser.new_page(user_agent=_get_random_user_agent())
            
            url = "https://pasport.org.ua/en/solutions/e-queue"
            log.info(f"Fetching {url}...")
            
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=45000)
                await page.wait_for_timeout(2000)
                
                content = await page.content()
                if "available" in content.lower() or "date" in content.lower():
                    log.info(f"Found {len(content)} bytes of content")
                    all_items.append({
                        "city": "Офіційно",
                        "service": "Запис",
                        "date": date.today().isoformat(),
                    })
                    
            except Exception as e:
                log.error(f"Error: {e}")
            finally:
                await page.close()
                await browser.close()
                
    except Exception as e:
        log.error(f"Browser error: {e}")
    
    return all_items
