import pandas as pd
import asyncio
import logging
import random
import time
from typing import List, Dict, Any
from playwright.async_api import async_playwright, Playwright, Page, TimeoutError, Error

# Configuration
CONFIG = {
    "base_url": "https://www.target.com/store-locator/store-directory",
    "output_csv": "target_stores_by_city.csv",
    "output_json": "target_stores_by_city.json",
    "timeout": 180000,  # Increased for reliability
    "max_concurrent": 2,  # Reduced to avoid detection
    "retry_attempts": 5,  # Increased retries
    "sleep_min": 5.0,  # Increased delays
    "sleep_max": 8.0,
    "user_agents": [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.2 Safari/605.1.15",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0",
    ],
    "viewport": {"width": 1280, "height": 800},
    "headless": True,  # Set False for debugging
}

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Global data store
scraped_data: List[Dict[str, str]] = []

async def emulate_human_behavior(page: Page) -> None:
    """Emulate human-like behavior to avoid detection (random mouse movement, scrolling, delays)."""
    # Random delay
    await asyncio.sleep(random.uniform(0.5, 1.5))
    # Random scroll
    scroll_y = random.randint(100, 800)
    await page.evaluate(f"window.scrollBy(0, {scroll_y});")
    # Random mouse movement (simulate by moving to a random point)
    box = await page.evaluate("""() => {
        return {width: window.innerWidth, height: window.innerHeight};
    }""")
    x = random.randint(0, box['width'] - 1)
    y = random.randint(0, box['height'] - 1)
    try:
        await page.mouse.move(x, y)
    except Exception:
        pass

async def get_state_urls(page: Page) -> List[Dict[str, str]]:
    """Fetch state URLs and names from the main directory page."""
    for attempt in range(CONFIG["retry_attempts"]):
        try:
            await page.goto(CONFIG["base_url"], timeout=CONFIG["timeout"], wait_until="domcontentloaded")
            await page.wait_for_function(
                """() => document.querySelectorAll('div.view_stateName__CzKvV a.view_stateNameLink__qdJ1N').length > 0""",
                timeout=CONFIG["timeout"]
            )
            state_links = await page.evaluate(
                """() => Array.from(document.querySelectorAll('div.view_stateName__CzKvV a.view_stateNameLink__qdJ1N'))
                    .map(el => ({ url: el.href, name: el.textContent.trim() }))"""
            )
            logger.info(f"Found {len(state_links)} state URLs")
            return state_links
        except (TimeoutError, Error) as e:
            logger.warning(f"Attempt {attempt + 1}/{CONFIG['retry_attempts']} failed for state URLs: {e}")
            if attempt < CONFIG["retry_attempts"] - 1:
                await asyncio.sleep(random.uniform(CONFIG["sleep_min"], CONFIG["sleep_max"]))
    logger.error("Failed to fetch state URLs after all retries")
    return []

async def get_city_urls(page: Page, state_url: str, state_name: str) -> List[Dict[str, str]]:
    """Fetch city URLs and names from a state page, including state name."""
    for attempt in range(CONFIG["retry_attempts"]):
        try:
            await page.goto(state_url, timeout=CONFIG["timeout"], wait_until="domcontentloaded")
            await page.wait_for_function(
                """() => document.querySelectorAll('div.view_cityName__vSrti a.view_cityNameLink__O_Xez').length > 0""",
                timeout=CONFIG["timeout"]
            )
            city_links = await page.evaluate(
                """() => Array.from(document.querySelectorAll('div.view_cityName__vSrti a.view_cityNameLink__O_Xez'))
                    .map(el => ({ url: el.href, name: el.textContent.trim() }))"""
            )
            for city in city_links:
                city["state"] = state_name
            logger.info(f"Fetched {len(city_links)} cities from {state_url}")
            return city_links
        except (TimeoutError, Error) as e:
            logger.warning(f"Attempt {attempt + 1}/{CONFIG['retry_attempts']} failed for cities at {state_url}: {e}")
            if attempt < CONFIG["retry_attempts"] - 1:
                await asyncio.sleep(random.uniform(CONFIG["sleep_min"], CONFIG["sleep_max"]))
    logger.error(f"Failed to fetch cities for {state_url} after all retries")
    return []

async def get_stores_in_city(page: Page, city_url: str, city_name: str, state_name: str) -> Dict[str, str]:
    """Fetch store names from a city page using two possible HTML formats."""
    for attempt in range(CONFIG["retry_attempts"]):
        try:
            # Try domcontentloaded first, fallback to networkidle
            try:
                response = await page.goto(city_url, timeout=CONFIG["timeout"], wait_until="domcontentloaded")
            except:
                logger.debug(f"Fallback to networkidle for {city_url}")
                response = await page.goto(city_url, timeout=CONFIG["timeout"], wait_until="networkidle")
            logger.debug(f"Store page status for {city_url}: {response.status}")
            await emulate_human_behavior(page)

            # Try first format: h3.styles_storeCardTitle__VFoDj
            try:
                await page.wait_for_function(
                    """() => document.querySelectorAll('h3.styles_storeCardTitle__VFoDj').length > 0""",
                    timeout=CONFIG["timeout"]
                )
                stores = await page.evaluate(
                    """() => Array.from(document.querySelectorAll('h3.styles_storeCardTitle__VFoDj'))
                        .map(el => el.childNodes[0].textContent.trim())"""
                )
                if stores:
                    store_string = ", ".join(stores)
                    logger.info(f"Fetched {len(stores)} stores for {city_name}, {state_name} using h3 format")
                    return {"State": state_name, "City": city_name, "Stores": store_string}
            except TimeoutError:
                logger.debug(f"No h3.styles_storeCardTitle__VFoDj found for {city_name}, trying span format")

            # Fallback to second format: span.styles_storeInfo__duma6
            try:
                await page.wait_for_function(
                    """() => document.querySelectorAll('span.styles_storeInfo__duma6').length > 0""",
                    timeout=CONFIG["timeout"]
                )
                stores = await page.evaluate(
                    """() => Array.from(document.querySelectorAll('span.styles_storeInfo__duma6'))
                        .map(el => {
                            const text = el.innerHTML.split('<br>')[1]?.trim();
                            return text ? text.split(',')[0].trim() : '';
                        }).filter(name => name)"""
                )
                store_string = ", ".join(stores) if stores else ""
                logger.info(f"Fetched {len(stores)} stores for {city_name}, {state_name} using span format")
                return {"State": state_name, "City": city_name, "Stores": store_string}
            except TimeoutError:
                logger.debug(f"No span.styles_storeInfo__duma6 found for {city_name}")

        except (TimeoutError, Error) as e:
            logger.warning(f"Attempt {attempt + 1}/{CONFIG['retry_attempts']} failed for {city_name}, {state_name}: {e}")
            try:
                content = await page.content()
                logger.debug(f"Store page content for {city_url}:\n{content[:500]}...")
            except Exception as debug_e:
                logger.debug(f"Failed to get store page content: {debug_e}")
            if attempt < CONFIG["retry_attempts"] - 1:
                await asyncio.sleep(random.uniform(CONFIG["sleep_min"], CONFIG["sleep_max"]))
    
    logger.warning(f"No stores found for {city_name}, {state_name} after all retries")
    return {"State": state_name, "City": city_name, "Stores": ""}

async def process_state(page: Page, state: Dict[str, str], semaphore: asyncio.Semaphore) -> List[Dict[str, str]]:
    """Process all cities for a given state."""
    async with semaphore:
        state_url = state["url"]
        state_name = state["name"]
        city_links = await get_city_urls(page, state_url, state_name)
        state_data = []
        for i in range(0, len(city_links), CONFIG["max_concurrent"]):
            batch = city_links[i:i + CONFIG["max_concurrent"]]
            tasks = [get_stores_in_city(page, city["url"], city["name"], city["state"]) for city in batch]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for result in results:
                if isinstance(result, Exception):
                    logger.error(f"Error in city batch: {result}")
                elif result["Stores"]:  # Only include cities with stores
                    state_data.append(result)
            await asyncio.sleep(random.uniform(CONFIG["sleep_min"], CONFIG["sleep_max"]))
        return state_data

async def scrape_target_stores() -> None:
    """Main function to scrape Target store data."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=CONFIG["headless"])
        context = await browser.new_context(
            user_agent=random.choice(CONFIG["user_agents"]),
            viewport=CONFIG["viewport"]
        )
        page = await context.new_page()
        semaphore = asyncio.Semaphore(CONFIG["max_concurrent"])

        state_links = await get_state_urls(page)
        if not state_links:
            logger.error("No state URLs found, exiting")
            await browser.close()
            return

        for state in state_links:
            state_data = await process_state(page, state, semaphore)
            scraped_data.extend(state_data)
            save_results()
            logger.info(f"Processed state {state['name']}, total records: {len(scraped_data)}")

        await browser.close()

def save_results() -> None:
    """Save scraped data to CSV and JSON."""
    if not scraped_data:
        logger.warning("No data to save")
        return

    df = pd.DataFrame(scraped_data)
    if not df.empty:
        df = df[["State", "City", "Stores"]]
        df.to_csv(CONFIG["output_csv"], index=False)
        df.to_json(CONFIG["output_json"], indent=2, orient="records")
        logger.info(f"Saved {len(df)} records to {CONFIG['output_csv']} and {CONFIG['output_json']}")

async def main() -> None:
    """Entry point for the scraper."""
    logger.info("Starting Target Store Scraper...")
    start_time = time.time()
    await scrape_target_stores()
    save_results()
    logger.info(f"Completed in {time.time() - start_time:.2f} seconds")

if __name__ == "__main__":
    asyncio.run(main())