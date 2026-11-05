import asyncio
import json
import logging
from datetime import datetime
from playwright.async_api import async_playwright
import random

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("browser-daemon")

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]

async def browser_loop():
    """Постійно завантажує сайт і зберігає дані"""
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True, args=[
                '--disable-blink-features=AutomationControlled',
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--disable-gpu',
            ])

            context = await browser.new_context(
                user_agent=random.choice(USER_AGENTS),
                viewport={'width': 1920, 'height': 1080},
                locale='uk-UA',
            )

            page = await context.new_page()
            url = "https://pasport.org.ua/en/solutions/e-queue"

            log.info("🌐 Браузер запущено, починаю завантажувати сайт...")

            # Перший запит одразу
            await asyncio.sleep(2)

            while True:
                try:
                    delay = random.uniform(180, 240)  # 3-4 хвилини між запитами
                    log.info(f"📡 Завантажую {url}... (наступний запит за {delay:.0f}сек)")

                    await page.goto(url, wait_until="networkidle", timeout=60000)
                    await page.wait_for_timeout(random.uniform(5000, 8000))

                    content = await page.content()
                    data = {
                        "timestamp": datetime.now().isoformat(),
                        "status": "success" if len(content) > 500 else "blocked",
                        "size": len(content),
                        "content": content[:10000],
                    }

                    with open('/home/ec2-user/browser_cache.json', 'w', encoding='utf-8') as f:
                        json.dump(data, f, ensure_ascii=False, indent=2)

                    log.info(f"✅ Дані збережені ({len(content)} байт)")

                    import re
                    dates = re.findall(r'(\d{4}-\d{2}-\d{2})', content)
                    if dates:
                        log.info(f"📅 Знайшов {len(set(dates))} дат: {list(set(dates))[:5]}")
                    else:
                        log.warning("⚠️ Дати не знайдені")

                    await asyncio.sleep(delay)

                except Exception as e:
                    log.error(f"❌ Помилка: {e}")
                    await asyncio.sleep(60)

            await browser.close()

    except Exception as e:
        log.error(f"🔴 Критична помилка: {e}")
        await asyncio.sleep(60)
        await browser_loop()

if __name__ == "__main__":
    asyncio.run(browser_loop())
