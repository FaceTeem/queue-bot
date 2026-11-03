#!/usr/bin/env python3
"""Test script for the queue parser."""
import asyncio
import logging
import sys

import config
from fetcher import fetch_dates

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s"
)
log = logging.getLogger("test")


async def main():
    log.info("=" * 60)
    log.info("Testing Queue Parser")
    log.info("=" * 60)
    log.info(f"Mode: {config.MODE}")
    log.info(f"Cities: {list(config.CITIES.keys())}")
    log.info(f"Services: {config.SERVICES}")
    log.info(f"Check Interval: {config.CHECK_INTERVAL}s")
    log.info("")

    try:
        log.info("Fetching dates...")
        dates = await fetch_dates()

        if not dates:
            log.warning("No dates found")
            return

        log.info(f"Found {len(dates)} open dates:")
        for item in dates:
            log.info(f"  • {item['city']} / {item['service']} @ {item['date']}")

        log.info("")
        log.info("✅ Parser works!")

    except Exception as e:
        log.error(f"❌ Parser failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
