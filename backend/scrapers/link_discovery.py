import time
import logging
from typing import List, Set, Dict
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from datetime import datetime
from urllib.parse import urlparse, urlunparse

from config import config

# ======== Logging Config ========
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

PAGINATION_SELECTORS = [
    'button[id="pagination-page-next"]',
    'button[aria-label*="next"]',
    '.pagination .next',
    '[data-testid="pagination-next"]',
    'a[class*="next"]'
]

# ======== Helper Functions ========
def get_chrome_driver() -> webdriver.Chrome:
    options = Options()
    if config.CHROME_OPTIONS.get("headless"):
        options.add_argument("--headless")
    if config.CHROME_OPTIONS.get("no_sandbox"):
        options.add_argument("--no-sandbox")
    if config.CHROME_OPTIONS.get("disable_dev_shm_usage"):
        options.add_argument("--disable-dev-shm-usage")
    if config.CHROME_OPTIONS.get("disable_gpu"):
        options.add_argument("--disable-gpu")
    if config.CHROME_OPTIONS.get("window_size"):
        options.add_argument(f"--window-size={config.CHROME_OPTIONS['window_size']}")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-infobars")
    try:
        service = Service()
        driver = webdriver.Chrome(service=service, options=options)
    except Exception as err:
        logger.warning(f"System chromedriver failed: {err}, trying local executable.")
        service = Service("chromedriver")
        driver = webdriver.Chrome(service=service, options=options)
    logger.info(f"Chrome WebDriver started. Headless mode: {config.CHROME_OPTIONS.get('headless', False)}")
    return driver

def scroll_to_bottom(driver, pause: float = 1.0, max_attempts: int = 5) -> None:
    last_height = driver.execute_script("return document.body.scrollHeight")
    for _ in range(max_attempts):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(pause)
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height

def click_tab_by_text(driver, tab_text: str) -> None:
    try:
        tabs = driver.find_elements(By.CSS_SELECTOR, '[role="tab"]')
        for tab in tabs:
            if tab.text.strip().lower() == tab_text.strip().lower():
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", tab)
                time.sleep(0.5)
                try:
                    tab.click()
                except Exception:
                    driver.execute_script("arguments[0].click();", tab)
                time.sleep(2)
                logger.info(f"Successfully clicked tab: '{tab_text}'")
                return
        logger.warning(f"Tab not found: '{tab_text}'")
    except Exception as e:
        logger.error(f"Error clicking tab '{tab_text}': {e}")

def click_next_page_in_container(container, driver) -> bool:
    for sel in PAGINATION_SELECTORS:
        try:
            buttons = container.find_elements(By.CSS_SELECTOR, sel)
            for button in buttons:
                if button.is_enabled() and button.is_displayed():
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", button)
                    time.sleep(0.5)
                    driver.execute_script("arguments[0].click();", button)
                    time.sleep(config.REQUEST_DELAY)
                    return True
        except Exception as err:
            logger.warning(f"Failed to click pagination button '{sel}': {err}")
    return False

def normalize_url(url: str) -> str:
    parsed = urlparse(url)
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, '', '', ''))

def is_valid_link(href: str) -> bool:
    if not href:
        return False
    parsed = urlparse(href)
    return any(part in parsed.path for part in ["/programs/", "/specialisations/", "/courses/"])

def click_specialisation_filter_button(driver, filter_text: str):
    try:
        nav = driver.find_element(By.CSS_SELECTOR, 'nav[aria-label="filters"]')
        buttons = nav.find_elements(By.TAG_NAME, "button")
        for btn in buttons:
            if filter_text.lower() in btn.text.strip().lower():
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn)
                time.sleep(0.5)
                try:
                    btn.click()
                except Exception:
                    driver.execute_script("arguments[0].click();", btn)
                logger.info(f"Clicked Specialisation filter: '{filter_text}'")
                time.sleep(2)
                return
        logger.warning(f"Specialisation filter not found: '{filter_text}'")
    except Exception as e:
        logger.error(f"Error clicking Specialisation '{filter_text}': {e}")

def extract_links_by_menu_title(driver, menu_title: str, need_special_filters=False) -> Set[str]:
    links_found = set()
    try:
        container = driver.find_element(By.CSS_SELECTOR, f'div[data-menu-title="{menu_title}"]')
    except Exception as e:
        logger.warning(f"Container with data-menu-title '{menu_title}' not found: {e}")
        return links_found

    def process_container():
        nonlocal links_found
        page_count = 1
        while True:
            logger.info(f"[{menu_title}] Scraping page {page_count}...")
            scroll_to_bottom(driver)
            links = container.find_elements(By.TAG_NAME, "a")
            logger.info(f"[{menu_title}] Found {len(links)} <a> tags on this page.")
            for link in links:
                href = link.get_attribute("href")
                if is_valid_link(href):
                    normalized = normalize_url(href)
                    links_found.add(normalized)
                    print(normalized)
            if not click_next_page_in_container(container, driver):
                logger.info(f"[{menu_title}] No more pages, stopping.")
                break
            page_count += 1

    if need_special_filters and menu_title == "Specialisations":
        for filter_type in ["Honours", "Major", "Minor"]:
            click_specialisation_filter_button(driver, filter_type)
            process_container()
    else:
        process_container()

    logger.info(f"[{menu_title}] Extracted total {len(links_found)} unique links.")
    return links_found

def discover_cse_links() -> Dict[str, List[str]]:
    driver = get_chrome_driver()
    final_results = {"programs": set(), "specialisations": set(), "courses": set()}
    root_url = config.CSE_BROWSE_URLS[0]

    try:
        logger.info(f"Opening root URL: {root_url}")
        driver.get(root_url)
        driver.set_page_load_timeout(config.PAGE_LOAD_TIMEOUT)
        time.sleep(3)

        tabs_to_scrape = ["Undergraduate", "Postgraduate", "Research"]
        for tab_name in tabs_to_scrape:
            logger.info(f"=== Processing tab '{tab_name}' ===")
            click_tab_by_text(driver, tab_name)

            for menu_title, key in [("Programs", "programs"), ("Double Degrees", "programs"),
                                    ("Specialisations", "specialisations"), ("Courses", "courses")]:
                logger.info(f"--- Scraping <div data-menu-title=\"{menu_title}\"> under '{tab_name}' ---")
                if tab_name == "Undergraduate" and menu_title == "Specialisations":
                    links = extract_links_by_menu_title(driver, menu_title, need_special_filters=True)
                else:
                    links = extract_links_by_menu_title(driver, menu_title)
                final_results[key].update(links)

            driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(1)

    except Exception as e:
        logger.error(f"Critical error during scraping: {e}")
    finally:
        logger.info("Scraping tasks complete, closing browser.")
        driver.quit()

    return {k: sorted(list(v)) for k, v in final_results.items()}

def save_links_to_file(links: Dict[str, List[str]]) -> None:
    filepath = config.URLS_FILE
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(f"# UNSW Handbook Links\n")
        f.write(f"# Auto-discovered on {datetime.now():%Y-%m-%d %H:%M:%S}\n\n")
        for category in ["programs", "specialisations", "courses"]:
            f.write(f"# === {category.upper()} ===\n")
            for url in links.get(category, []):
                f.write(f"{url}\n")
            f.write("\n")
    logger.info(f"Successfully saved all links to: {filepath}")

def discover_and_save_cse_links() -> Dict[str, List[str]]:
    links = discover_cse_links()
    total_links = sum(len(v) for v in links.values())
    if total_links > 0:
        save_links_to_file(links)
    else:
        logger.warning("No links discovered, file not generated.")
    return links

if __name__ == "__main__":
    logger.info("Starting link discovery module...")
    logger.info("Ensuring output directories exist...")
    config.ensure_directories()
    discovered = discover_and_save_cse_links()
    logger.info("--- Scraping summary ---")
    for category, link_list in discovered.items():
        logger.info(f"Discovered {len(link_list)} {category} links.")
    logger.info("------------------------")
