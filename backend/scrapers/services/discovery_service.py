"""
Link discovery service - finding and extracting links from UNSW handbook
"""

import time
import logging
from typing import List, Dict, Set
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

from ..core.base import BaseScraper
from ..core.exceptions import WebDriverError
from ..config import config
from ..utils.web_utils import (
    get_chrome_driver,
    scroll_to_bottom,
    click_tab_by_text,
    normalize_url,
    is_valid_link
)
from ..utils.file_utils import save_links_to_file

logger = logging.getLogger(__name__)

PAGINATION_SELECTORS = [
    'button[id="pagination-page-next"]',
    'button[aria-label*="next"]',
    '.pagination .next',
    '[data-testid="pagination-next"]',
    'a[class*="next"]'
]

class UNSWLinkDiscoveryService(BaseScraper):
    """Service for discovering links from UNSW handbook browse pages"""
    
    def __init__(self):
        self.driver = None
    
    def _get_driver(self):
        """Get or create Chrome driver"""
        if self.driver is None:
            self.driver = get_chrome_driver()
        return self.driver
    
    def _close_driver(self):
        """Close Chrome driver"""
        if self.driver:
            self.driver.quit()
            self.driver = None
    
    def click_specialisation_filter_button(self, driver, filter_text: str):
        """Click specialisation filter button"""
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
    
    def click_next_page_in_container(self, container, driver) -> bool:
        """Click next page button in container and wait for content to change"""
        # Get current page links before clicking
        current_links = set()
        try:
            links = container.find_elements(By.TAG_NAME, "a")
            for link in links:
                href = link.get_attribute("href")
                if is_valid_link(href):
                    current_links.add(normalize_url(href))
        except Exception:
            pass
        
        for sel in PAGINATION_SELECTORS:
            try:
                buttons = container.find_elements(By.CSS_SELECTOR, sel)
                for button in buttons:
                    if button.is_enabled() and button.is_displayed():
                        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", button)
                        time.sleep(0.5)
                        driver.execute_script("arguments[0].click();", button)
                        
                        # Wait for page content to change (up to 10 seconds)
                        max_wait_attempts = 20  # 20 * 0.5s = 10s max wait
                        for attempt in range(max_wait_attempts):
                            time.sleep(0.5)
                            
                            # Check if content has changed
                            try:
                                new_links = set()
                                links = container.find_elements(By.TAG_NAME, "a")
                                for link in links:
                                    href = link.get_attribute("href")
                                    if is_valid_link(href):
                                        new_links.add(normalize_url(href))
                                
                                # If we have different links, page has loaded
                                if new_links != current_links and len(new_links) > 0:
                                    logger.info(f"Page content changed after {(attempt + 1) * 0.5:.1f}s")
                                    return True
                                    
                            except Exception as e:
                                logger.warning(f"Error checking page change: {e}")
                                continue
                        
                        logger.warning("Page content did not change after clicking next page")
                        return False
                        
            except Exception as err:
                logger.warning(f"Failed to click pagination button '{sel}': {err}")
        return False
    
    def extract_links_by_menu_title(self, driver, menu_title: str, need_special_filters=False) -> Set[str]:
        """Extract links from container by menu title"""
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
                if not self.click_next_page_in_container(container, driver):
                    logger.info(f"[{menu_title}] No more pages, stopping.")
                    break
                page_count += 1

        if need_special_filters and menu_title == "Specialisations":
            for filter_type in ["Honours", "Major", "Minor"]:
                self.click_specialisation_filter_button(driver, filter_type)
                process_container()
        else:
            process_container()

        logger.info(f"[{menu_title}] Extracted total {len(links_found)} unique links.")
        return links_found
    
    def scrape_links(self, root_url: str) -> Dict[str, List[str]]:
        """Discover links from UNSW handbook browse page"""
        driver = self._get_driver()
        final_results = {"programs": set(), "specialisations": set(), "courses": set()}

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
                        links = self.extract_links_by_menu_title(driver, menu_title, need_special_filters=True)
                    else:
                        links = self.extract_links_by_menu_title(driver, menu_title)
                    final_results[key].update(links)

                driver.execute_script("window.scrollTo(0, 0);")
                time.sleep(1)

        except Exception as e:
            logger.error(f"Critical error during scraping: {e}")
            raise WebDriverError(f"Link discovery failed: {e}")
        finally:
            self._close_driver()

        return {k: sorted(list(v)) for k, v in final_results.items()}
    
    def scrape_content(self, url: str, options) -> None:
        """Not implemented for discovery service"""
        raise NotImplementedError("Discovery service doesn't scrape content")
    
    def batch_scrape(self, urls: List[str], options) -> None:
        """Not implemented for discovery service"""
        raise NotImplementedError("Discovery service doesn't scrape content")

# Convenience functions for backward compatibility
def discover_cse_links(browse_url: str = config.CSE_BROWSE_URLS[0]) -> Dict[str, List[str]]:
    """Discover CSE links using the service"""
    service = UNSWLinkDiscoveryService()
    return service.scrape_links(browse_url)

def discover_and_save_cse_links(browse_url: str = config.CSE_BROWSE_URLS[0]) -> Dict[str, List[str]]:
    """Discover links and save them to file"""
    service = UNSWLinkDiscoveryService()
    links = service.scrape_links(browse_url)
    total_links = sum(len(v) for v in links.values())
    if total_links > 0:
        save_links_to_file(links)
    else:
        logger.warning("No links discovered, file not generated.")
    return links

def discover_cse_links_with_preview(root_url: str, existing_urls: Set[str]) -> Dict:
    """
    Discover links and return detailed preview for admin review
    """
    # Run discovery
    discovered_links = discover_cse_links()
    
    # Convert to flat list of all discovered URLs
    all_discovered = []
    categories = {}
    
    for category, urls in discovered_links.items():
        categories[category] = len(urls)
        all_discovered.extend(urls)
    
    # Identify new vs existing links
    all_discovered_set = set(all_discovered)
    new_urls = all_discovered_set - existing_urls
    existing_count = len(all_discovered_set & existing_urls)
    
    # Create preview of new links (first 10)
    new_links_preview = []
    for url in list(new_urls)[:10]:
        # Try to extract title from URL
        try:
            url_parts = url.split('/')
            if len(url_parts) >= 2:
                code_or_id = url_parts[-1]
                category = 'course' if 'courses' in url else ('program' if 'programs' in url else 'specialisation')
                title = f"{category.title()} {code_or_id}"
            else:
                title = "Unknown"
        except:
            title = "Unknown"
            
        new_links_preview.append({
            "url": url,
            "title": title,
            "accessible": True  # TODO: Could add actual accessibility check
        })
    
    # Quality check (simplified for now)
    quality_check = {
        "all_accessible": True,  # TODO: Implement actual checks
        "structure_validated": True,
        "duplicate_warnings": 0
    }
    
    return {
        "total_links": len(all_discovered),
        "new_links_count": len(new_urls), 
        "existing_links_count": existing_count,
        "categories": categories,
        "new_links_preview": new_links_preview,
        "quality_check": quality_check,
        "all_links": discovered_links  # For saving after confirmation
    }