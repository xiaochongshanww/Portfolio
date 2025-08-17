from playwright.sync_api import sync_playwright
from playwright_stealth.stealth import Stealth
import time
import random
import os
import logging
from urllib.parse import urlparse, parse_qs, urlunparse

logger = logging.getLogger(__name__)

AUTH_FILE = 'playwright_auth.json'

def clean_url(url: str) -> str:
    """Cleans the Taobao/Tmall URL to its essential parts to avoid redirects."""
    try:
        parsed_url = urlparse(url)
        query_params = parse_qs(parsed_url.query)
        # Keep only the 'id' parameter
        if 'id' in query_params:
            clean_query = f"id={query_params['id'][0]}"
            # Reconstruct the URL with only the essential parts
            clean_url = urlunparse((
                parsed_url.scheme,
                parsed_url.netloc,
                parsed_url.path,
                '',
                clean_query,
                ''
            ))
            logger.info(f"Cleaned URL from '{url}' to '{clean_url}'")
            return clean_url
    except Exception as e:
        logger.error(f"Could not clean URL {url}: {e}")
    # If cleaning fails, return the original URL
    return url

def scrape_product(url: str):
    name = None
    price = None
    
    original_url = url
    url = clean_url(original_url)

    logger.info(f"Starting to scrape URL: {url}")

    stealth = Stealth()
    with stealth.use_sync(sync_playwright()) as p:
        browser = p.chromium.launch(channel="chrome", headless=headless)
        try:
            storage_state = AUTH_FILE if os.path.exists(AUTH_FILE) else None
            logger.debug(f"Loading storage state from: {storage_state}")
            context = browser.new_context(storage_state=storage_state, proxy=proxy_config)
            page = context.new_page()

            logger.debug("Navigating to page...")
            page.goto(url, wait_until='domcontentloaded', timeout=60000)
            logger.debug("Page navigation complete.")

            logger.info("Waiting for 20 seconds for page to settle...")
            page.wait_for_timeout(20000)
            logger.info("Wait finished. Attempting to scrape data...")

            # ... (rest of the scraping logic remains the same)
            price_selectors = [
                'div.Price--priceWrapper--ptUryMv span.Price--priceText--I_v3_2i',
                'span.Price--priceText--I_v3_2i',
                'div.Price--price--m3f0L9w span.Price--priceText--I_v3_2i',
                '[class*="Price--priceText"]',
                '[class*="Price--realPrice--"]',
                '[class*="Price--seckillPrice--"]',
                'span.price',
                'em.price'
            ]
            for selector in price_selectors:
                try:
                    price_text = page.locator(selector).first.inner_text(timeout=5000)
                    logger.debug(f"Found price text: '{price_text}' with selector: '{selector}'")
                    price = float("".join(filter(lambda char: char.isdigit() or char == '.', price_text)))
                    if price > 0:
                        logger.info(f"Successfully parsed price: {price}")
                        break
                except Exception:
                    logger.debug(f"Selector '{selector}' failed. Trying next.")
                    continue
            if not price:
                 logger.warning("Could not find price with any selector.")

            name_selectors = [
                'div.Title--title--jYI3_5r',
                'h1[class*="Title--title--"]',
                '#J_Title > h3',
                'div.tb-detail-hd > h1'
            ]
            for selector in name_selectors:
                try:
                    name = page.locator(selector).first.inner_text(timeout=5000)
                    if name:
                        name = name.strip()
                        logger.info(f"Successfully parsed name: {name}")
                        break
                except Exception:
                    logger.debug(f"Selector '{selector}' failed. Trying next.")
                    continue
            
            if not name:
                name = page.title().strip()
                logger.info(f"Could not find name element, falling back to page title: '{name}'")

            logger.debug(f"Saving storage state to {AUTH_FILE}")
            context.storage_state(path=AUTH_FILE)

        except Exception as e:
            logger.error(f"An error occurred while scraping {original_url}: {e}", exc_info=True)
            # Take a screenshot on error for debugging
            if 'page' in locals():
                screenshot_path = "debug_screenshot.png"
                try:
                    page.screenshot(path=screenshot_path, full_page=True)
                    logger.info(f"Screenshot saved to {screenshot_path} for debugging.")
                except Exception as se:
                    logger.error(f"Failed to take screenshot: {se}")
        finally:
            logger.debug("Closing browser.")
            browser.close()

    logger.info(f"Scraping finished. Name='{name}', Price={price}")
    return name, price
