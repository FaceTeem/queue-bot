"""Where the bot gets data about open dates.

Every item is a dict: {"city", "service", "date"} — one open day in the queue.
Uses Playwright to bypass Cloudflare and extract available dates from pasport.org.ua.
Demo mode returns random fake dates for testing.
Live mode uses Playwright browser automation to check each city/service combination.

Anti-bot strategy:
- Checks every 5 minutes (300s) = 288 checks/day per city
- Adds 30-90s random jitter to avoid patterns
- 1-3s delay between cities
- Realistic User-Agent rotation
- Exponential backoff on errors
"""
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

# Realistic User-Agent rotation to avoid bot detection
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
]

def _get_random_user_agent() -> str:
    """Get a random realistic User-Agent."""
    return random.choice(USER_AGENTS)


class SessionExpired(Exception):
    """Raised when the site blocks access (Cloudflare, 401/403)."""


def _demo_dates():
    items = []
    if random.random() < 0.4:  # sometimes the queue is closed everywhere
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


async def fetch_dates(http=None) -> list[dict]:
    if config.MODE == "demo":
        return _demo_dates()
    return await _live_dates()


async def _live_dates() -> list[dict]:
    """Fetch real dates using Playwright to bypass Cloudflare."""
    if not async_playwright:
        raise Exception("Playwright not installed. Install with: pip install playwright")

    all_items = []
    cities_list = list(config.CITIES.items())

    for idx, (city_name, city_code) in enumerate(cities_list):
        # Delay between cities to look more human (1-3s)
        if idx > 0:
            delay = random.uniform(1, 3)
            await asyncio.sleep(delay)

        try:
            url = f"https://{city_code}.pasport.org.ua/solutions/e-queue"
            log.info(f"Checking {city_name}...")

            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,
                    args=['--disable-blink-features=AutomationControlled']
                )
                page = await browser.new_page(
                    user_agent=_get_random_user_agent()
                )

                try:
                    await page.goto(url, wait_until="domcontentloaded", timeout=45000)
                    await page.wait_for_timeout(2000)

                    # Try to bypass Cloudflare
                    try:
                        checkbox = await page.query_selector("input[type='checkbox']")
                        if checkbox:
                            log.debug(f"Clicking Cloudflare checkbox for {city_name}")
                            await checkbox.click()
                            await page.wait_for_timeout(3000)
                    except:
                        pass

                    # Try Method 1: Select dropdown (format A)
                    service_select = await page.query_selector("select[name='service']")
                    if service_select:
                        options = await page.query_selector_all("select[name='service'] option")
                        log.debug(f"Found {len(options)} services in {city_name}")

                        for idx, option in enumerate(options[1:], start=1):
                            service_text = await option.text_content()
                            service_text = service_text.strip() if service_text else f"Service {idx}"

                            try:
                                await service_select.select_option(index=idx)
                                await page.wait_for_timeout(1000)

                                has_slots = await _check_for_available_dates(page)
                                if has_slots:
                                    dates = await _extract_dates(page)
                                    for d in dates:
                                        all_items.append({
                                            "city": city_name,
                                            "service": service_text,
                                            "date": d,
                                        })
                                        log.info(f"Found {d} for {city_name}/{service_text}")
                            except Exception as e:
                                log.debug(f"Error checking {service_text} in {city_name}: {e}")

                    else:
                        # Try Method 2: Radio buttons or buttons (format B)
                        log.debug(f"No select dropdown found, trying other methods for {city_name}")

                        # Try radio buttons for services
                        radios = await page.query_selector_all("input[type='radio'][name='service']")
                        if radios:
                            log.debug(f"Found {len(radios)} radio buttons for services")
                            for idx, radio in enumerate(radios):
                                try:
                                    service_text = await radio.get_attribute("value")
                                    if not service_text:
                                        label = await page.query_selector(f"label[for='{await radio.get_attribute('id')}']")
                                        if label:
                                            service_text = await label.text_content()

                                    service_text = service_text.strip() if service_text else f"Service {idx}"

                                    await radio.click()
                                    await page.wait_for_timeout(1000)

                                    has_slots = await _check_for_available_dates(page)
                                    if has_slots:
                                        dates = await _extract_dates(page)
                                        for d in dates:
                                            all_items.append({
                                                "city": city_name,
                                                "service": service_text,
                                                "date": d,
                                            })
                                            log.info(f"Found {d} for {city_name}/{service_text}")
                                except Exception as e:
                                    log.debug(f"Error with radio button: {e}")

                        else:
                            # Try Method 3: Just check for available dates without service selection
                            log.debug(f"No service radios found either, checking for general availability")
                            has_slots = await _check_for_available_dates(page)
                            if has_slots:
                                dates = await _extract_dates(page)
                                for d in dates:
                                    all_items.append({
                                        "city": city_name,
                                        "service": "Послуга",
                                        "date": d,
                                    })
                                    log.info(f"Found {d} for {city_name}")

                finally:
                    await page.close()
                    await browser.close()

        except Exception as e:
            log.error(f"Error checking {city_name}: {e}")
            continue

    return all_items


async def _check_for_available_dates(page) -> bool:
    """Check if there are available dates."""
    try:
        date_select = await page.query_selector("select[name='date']")
        if date_select:
            options = await page.query_selector_all("select[name='date'] option")
            has_dates = len(options) > 1
            log.debug(f"Date select found: {len(options)} options (has dates: {has_dates})")
            return has_dates
    except Exception as e:
        log.debug(f"Error checking select[name='date']: {e}")

    try:
        # Try alternative date selectors
        alt_selects = await page.query_selector_all("select")
        log.debug(f"Found {len(alt_selects)} select elements total")
        for idx, sel in enumerate(alt_selects):
            name = await sel.get_attribute("name")
            options = await sel.query_selector_all("option")
            log.debug(f"  Select {idx}: name={name}, options={len(options)}")
    except:
        pass

    try:
        content = await page.content()
        has_available = "available" in content.lower() or "доступні" in content.lower()
        log.debug(f"Page has 'available'/'доступні': {has_available}")
        return has_available
    except Exception as e:
        log.debug(f"Error checking page content: {e}")

    return False


async def _extract_dates(page) -> list[str]:
    """Extract available dates from the page."""
    dates = []

    try:
        date_select = await page.query_selector("select[name='date']")
        if date_select:
            options = await page.query_selector_all("select[name='date'] option")
            for option in options[1:]:
                value = await option.get_attribute("value")
                if value and value.strip():
                    dates.append(value)
    except:
        pass

    return list(set(dates))
