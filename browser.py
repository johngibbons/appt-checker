from __future__ import annotations

import logging
import os
import re
from datetime import date, datetime

from playwright.async_api import Page, async_playwright

import config

log = logging.getLogger(__name__)


async def _save_debug_screenshot(page: Page, name: str) -> None:
    os.makedirs(config.DEBUG_DIR, exist_ok=True)
    path = os.path.join(config.DEBUG_DIR, f"{name}.png")
    try:
        await page.screenshot(path=path, full_page=True)
        log.info("Debug screenshot saved: %s", path)
    except Exception:
        log.exception("Failed to save debug screenshot")


async def _discover_iframe_url(page: Page) -> str | None:
    """Try to extract the NexHealth iframe src from the appointments page."""
    log.info("Attempting to discover NexHealth iframe URL from %s", config.ARYADERM_APPOINTMENTS_URL)
    await page.goto(config.ARYADERM_APPOINTMENTS_URL, wait_until="networkidle", timeout=30000)
    await page.wait_for_timeout(3000)

    # Try multiple selectors for the iframe
    for selector in ["#aryadermApointment", "iframe[src*='nexhealth']", "iframe[src*='booking']"]:
        try:
            iframe = page.locator(selector).first
            src = await iframe.get_attribute("src", timeout=5000)
            if src:
                log.info("Discovered iframe URL: %s", src)
                return src
        except Exception:
            continue

    await _save_debug_screenshot(page, "iframe_discovery_failed")
    return None


async def _select_provider(page: Page) -> bool:
    """Click on one of the target providers."""
    log.info("Looking for providers: %s", config.PROVIDER_NAMES)
    await page.wait_for_timeout(2000)

    for provider_name in config.PROVIDER_NAMES:
        # Try common patterns for provider selection elements
        for selector in [
            f"text=/{provider_name}/i",
            f"button:has-text('{provider_name}')",
            f"div:has-text('{provider_name}')",
            f"[data-provider-name*='{provider_name}' i]",
            f"a:has-text('{provider_name}')",
        ]:
            try:
                locator = page.locator(selector).first
                if await locator.is_visible(timeout=2000):
                    await locator.click()
                    log.info("Selected provider: %s", provider_name)
                    await page.wait_for_timeout(2000)
                    return True
            except Exception:
                continue

    await _save_debug_screenshot(page, "provider_selection_failed")
    log.error("Could not find any target provider")
    return False


async def _select_appointment_type(page: Page) -> bool:
    """Click on the follow-up / existing patient appointment type."""
    log.info("Looking for appointment type: %s", config.APPOINTMENT_TYPE)
    await page.wait_for_timeout(2000)

    for selector in [
        f"text=/{config.APPOINTMENT_TYPE}/i",
        f"button:has-text('{config.APPOINTMENT_TYPE}')",
        f"div:has-text('{config.APPOINTMENT_TYPE}')",
        f"a:has-text('{config.APPOINTMENT_TYPE}')",
    ]:
        try:
            locator = page.locator(selector).first
            if await locator.is_visible(timeout=2000):
                await locator.click()
                log.info("Selected appointment type: %s", config.APPOINTMENT_TYPE)
                await page.wait_for_timeout(2000)
                return True
        except Exception:
            continue

    await _save_debug_screenshot(page, "appointment_type_failed")
    log.error("Could not find appointment type: %s", config.APPOINTMENT_TYPE)
    return False


def _parse_ordinal_date(text: str) -> date | None:
    """Parse dates like 'April 16th, 2026' or 'Mon April 27th'."""
    # Remove ordinal suffixes (st, nd, rd, th)
    cleaned = re.sub(r'(\d+)(st|nd|rd|th)', r'\1', text.strip())
    # Try with year
    for fmt in ("%B %d, %Y", "%B %d %Y", "%A %B %d %Y", "%a %B %d %Y", "%a %B %d"):
        try:
            parsed = datetime.strptime(cleaned, fmt).date()
            # If no year was in format, assume current year
            if parsed.year == 1900:
                parsed = parsed.replace(year=date.today().year)
            return parsed
        except ValueError:
            continue
    return None


async def _scrape_earliest_date(page: Page) -> date | None:
    """Find the earliest available date from the NexHealth calendar view."""
    log.info("Scraping calendar for available dates...")
    await page.wait_for_timeout(3000)

    available_dates: list[date] = []

    # Strategy 1: Date column headers with aria-label (e.g., "April 16th, 2026")
    # These are the visible time-slot columns for the selected provider
    date_columns = page.locator("div[aria-label]")
    count = await date_columns.count()
    for i in range(count):
        el = date_columns.nth(i)
        label = await el.get_attribute("aria-label")
        if not label:
            continue
        parsed = _parse_ordinal_date(label)
        if parsed and parsed >= date.today():
            available_dates.append(parsed)
            log.info("Found date column: %s -> %s", label, parsed.isoformat())

    # Strategy 2: "Next available appointment" text (for other providers listed below)
    try:
        html = await page.content()
        next_avail_matches = re.findall(
            r'(?:Next available|next available)[^<]*?(?:on\s+)(\w+\s+\w+\s+\d+\w*)',
            html,
        )
        for match in next_avail_matches:
            parsed = _parse_ordinal_date(match)
            if parsed and parsed >= date.today():
                available_dates.append(parsed)
                log.info("Found 'next available' date: %s -> %s", match, parsed.isoformat())
    except Exception:
        log.exception("Error parsing 'next available' text")

    if not available_dates:
        await _save_debug_screenshot(page, "calendar_scrape_failed")
        try:
            html = await page.content()
            html_path = os.path.join(config.DEBUG_DIR, "calendar_page.html")
            os.makedirs(config.DEBUG_DIR, exist_ok=True)
            with open(html_path, "w") as f:
                f.write(html)
            log.info("Page HTML saved to %s", html_path)
        except Exception:
            pass
        log.error("Could not find any available dates on the calendar")
        return None

    earliest = min(available_dates)
    log.info("Earliest available date: %s (from %d candidates)", earliest.isoformat(), len(available_dates))
    return earliest


async def check_availability() -> date | None:
    """Full flow: open booking page, select provider/type, scrape earliest date."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=config.HEADLESS)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 900},
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        )
        page = await context.new_page()

        try:
            # Step 1: Navigate to booking page
            if config.NEXHEALTH_BOOKING_URL:
                log.info("Navigating to NexHealth URL: %s", config.NEXHEALTH_BOOKING_URL)
                await page.goto(config.NEXHEALTH_BOOKING_URL, wait_until="networkidle", timeout=30000)
            else:
                # Try to discover the iframe URL
                iframe_url = await _discover_iframe_url(page)
                if iframe_url:
                    log.info("Navigating to discovered iframe URL: %s", iframe_url)
                    await page.goto(iframe_url, wait_until="networkidle", timeout=30000)
                else:
                    log.warning("No iframe URL found. Using main page — selectors may need adjustment.")
                    # Try to interact with the iframe directly on the page
                    await page.goto(config.ARYADERM_APPOINTMENTS_URL, wait_until="networkidle", timeout=30000)

            await page.wait_for_timeout(2000)
            await _save_debug_screenshot(page, "01_page_loaded")

            # Step 2: Select appointment type (shown first in NexHealth widget)
            if not await _select_appointment_type(page):
                return None
            await _save_debug_screenshot(page, "02_type_selected")

            # Step 3: Select provider
            if not await _select_provider(page):
                return None
            await _save_debug_screenshot(page, "03_provider_selected")

            # Step 4: Scrape earliest date
            earliest = await _scrape_earliest_date(page)
            await _save_debug_screenshot(page, "04_calendar")
            return earliest

        except Exception:
            log.exception("Error during availability check")
            await _save_debug_screenshot(page, "error")
            return None
        finally:
            await browser.close()
