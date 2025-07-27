"""
Web scraping utilities - WebDriver setup, HTTP requests, URL handling
"""

import time
import random
import logging
from typing import Optional, Dict
from urllib.parse import urlparse, urlunparse

import requests
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

from ..config import config
from ..core.exceptions import WebDriverError, NetworkError

logger = logging.getLogger(__name__)

def get_chrome_driver() -> webdriver.Chrome:
    """Create and configure Chrome WebDriver instance"""
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
        try:
            service = Service("chromedriver")
            driver = webdriver.Chrome(service=service, options=options)
        except Exception as e:
            raise WebDriverError(f"Failed to initialize Chrome WebDriver: {e}")
    
    logger.info(f"Chrome WebDriver started. Headless mode: {config.CHROME_OPTIONS.get('headless', False)}")
    return driver

def get_random_headers() -> Dict[str, str]:
    """Generate randomized headers to avoid detection"""
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:120.0) Gecko/20100101 Firefox/120.0"
    ]
    
    accept_languages = [
        "en-US,en;q=0.9",
        "en-AU,en;q=0.9,en-US;q=0.8",
        "en-GB,en;q=0.9,en-US;q=0.8",
        "en-US,en;q=0.5"
    ]
    
    return {
        "User-Agent": random.choice(user_agents),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": random.choice(accept_languages),
        "Accept-Encoding": "gzip, deflate, br",
        "Accept-Charset": "UTF-8",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Cache-Control": "max-age=0"
    }

def add_random_delay(min_delay: float = 1.0, max_delay: float = 3.0):
    """Add random delay between requests to avoid rate limiting"""
    delay = random.uniform(min_delay, max_delay)
    print(f"⏱️ Waiting {delay:.1f}s before next request...")
    time.sleep(delay)

def make_request_with_retry(url: str, max_retries: int = 3, backoff_factor: float = 2.0) -> Optional[requests.Response]:
    """Make HTTP request with retries and exponential backoff"""
    for attempt in range(max_retries):
        try:
            headers = get_random_headers()
            
            # Add delay before request (except first attempt)
            if attempt > 0:
                delay = backoff_factor ** attempt + random.uniform(0.5, 1.5)
                print(f"🔄 Retry {attempt + 1}/{max_retries} after {delay:.1f}s delay...")
                time.sleep(delay)
            
            response = requests.get(url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                return response
            elif response.status_code == 403:
                print(f"⛔ HTTP 403 Forbidden - attempt {attempt + 1}/{max_retries}")
                if attempt < max_retries - 1:
                    continue
            elif response.status_code == 429:
                print(f"⏳ Rate limited (429) - attempt {attempt + 1}/{max_retries}")
                if attempt < max_retries - 1:
                    time.sleep(random.uniform(5, 10))
                    continue
            else:
                response.raise_for_status()
                
        except requests.exceptions.RequestException as e:
            print(f"🌐 Network error on attempt {attempt + 1}/{max_retries}: {e}")
            if attempt < max_retries - 1:
                continue
            
    print(f"❌ Failed to fetch {url} after {max_retries} attempts")
    return None

def normalize_url(url: str) -> str:
    """Normalize URL by removing query parameters and fragments"""
    parsed = urlparse(url)
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, '', '', ''))

def is_valid_link(href: str) -> bool:
    """Check if URL is a valid UNSW handbook link"""
    if not href:
        return False
    parsed = urlparse(href)
    return any(part in parsed.path for part in ["/programs/", "/specialisations/", "/courses/"])

def scroll_to_bottom(driver, pause: float = 1.0, max_attempts: int = 5) -> None:
    """Scroll to bottom of page to load dynamic content"""
    last_height = driver.execute_script("return document.body.scrollHeight")
    for _ in range(max_attempts):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(pause)
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height

def click_tab_by_text(driver, tab_text: str) -> None:
    """Click tab element by its text content"""
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