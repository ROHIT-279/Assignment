from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import (
    TimeoutException, 
    NoSuchElementException, 
    ElementClickInterceptedException,
    StaleElementReferenceException,
    WebDriverException
)
import time
import pandas as pd
import logging
import re
from datetime import datetime
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import queue

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(threadName)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('trivago_scraper_improved.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class TrivagoImprovedScraper:
    def __init__(self, headless=False, max_workers=5):
        self.hotels_data = []
        self.data_lock = threading.Lock()
        self.headless = headless
        self.max_workers = max_workers
        self.total_pages = 12
        
    def setup_driver(self):
        """Setup Chrome driver with optimized options"""
        options = Options()
        options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-web-security")
        options.add_argument("--disable-features=VizDisplayCompositor")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-plugins")
        options.add_argument("--disable-images")  # Faster loading
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        if self.headless:
            options.add_argument("--headless")
        
        # Performance optimizations
        prefs = {
            "profile.default_content_setting_values": {
                "images": 2,
                "plugins": 2,
                "popups": 2,
                "geolocation": 2,
                "notifications": 2,
                "media_stream": 2,
            }
        }
        options.add_experimental_option("prefs", prefs)
        
        try:
            driver = webdriver.Chrome(options=options)
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            return driver
        except Exception as e:
            logger.error(f"Failed to initialize Chrome driver: {e}")
            return None
    
    def get_all_page_numbers(self, driver):
        """Get all available page numbers from pagination"""
        try:
            # Wait for pagination to load
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CLASS_NAME, "_8jzFmD"))
            )
            
            # Find all pagination list items
            page_li_elements = driver.find_elements(By.CLASS_NAME, "_8jzFmD")
            
            if not page_li_elements:
                logger.warning("No pagination elements found")
                return []
            
            available_pages = []
            
            for li_element in page_li_elements:
                try:
                    # Find button with class y3QF3R
                    button_elements = li_element.find_elements(By.CLASS_NAME, "y3QF3R")
                    
                    if button_elements:
                        button = button_elements[0]
                        button_text = button.text.strip()
                        
                        # Check if it's a number (page number)
                        if button_text.isdigit():
                            page_num = int(button_text)
                            
                            # Check if it's current page based on your info
                            data_test_id = button.get_attribute('data-testid') or ''
                            button_classes = button.get_attribute('class') or ''
                            
                            # Current page indicators: IffbQ9 class or "current" in data-testid
                            is_current = ('IffbQ9' in button_classes or 
                                        'current' in data_test_id.lower())
                            
                            available_pages.append({
                                'page_number': page_num,
                                'element': button,
                                'is_current': is_current,
                                'data_testid': data_test_id,
                                'classes': button_classes
                            })
                            
                            logger.debug(f"Found page {page_num} (current: {is_current})")
                            
                except Exception as e:
                    logger.debug(f"Error processing pagination element: {e}")
                    continue
            
            # Sort by page number
            available_pages.sort(key=lambda x: x['page_number'])
            
            page_numbers = [p['page_number'] for p in available_pages]
            logger.info(f"Found {len(available_pages)} pages: {page_numbers}")
            
            # If we found fewer than 12 pages, assume pages 1-12 exist
            if len(page_numbers) < 12:
                logger.info(f"Only found {len(page_numbers)} pages in pagination, assuming pages 1-12 exist")
                return list(range(1, 13))
            
            return page_numbers
            
        except Exception as e:
            logger.error(f"Error getting page numbers: {e}")
            # Fallback to assume 1-12 pages exist
            return list(range(1, 13))
    
    def navigate_to_page_by_url(self, driver, base_url, page_number):
        """Navigate to a specific page using URL manipulation"""
        try:
            if page_number == 1:
                # First page is the base URL
                driver.get(base_url)
            else:
                # For other pages, we need to construct the URL or use pagination
                # First load the base page
                driver.get(base_url)
                
                # Wait for page to load
                WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "_8jzFmD"))
                )
                
                # Try to find and click the page number
                if not self.click_page_number(driver, page_number):
                    logger.warning(f"Could not navigate to page {page_number} via pagination")
                    return False
            
            # Wait for content to load
            time.sleep(2)
            
            # Verify page loaded
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".g3BCYF, [data-testid='item'], .item"))
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error navigating to page {page_number}: {e}")
            return False
    
    def click_page_number(self, driver, target_page):
        """Click on a specific page number in pagination"""
        try:
            # Get all pagination elements
            page_li_elements = driver.find_elements(By.CLASS_NAME, "_8jzFmD")
            
            for li_element in page_li_elements:
                try:
                    button_elements = li_element.find_elements(By.CLASS_NAME, "y3QF3R")
                    
                    if button_elements:
                        button = button_elements[0]
                        button_text = button.text.strip()
                        
                        if button_text.isdigit() and int(button_text) == target_page:
                            # Check if it's already current
                            data_test_id = button.get_attribute('data-testid') or ''
                            button_classes = button.get_attribute('class') or ''
                            
                            is_current = ('IffbQ9' in button_classes or 
                                        'current' in data_test_id.lower())
                            
                            if is_current:
                                logger.info(f"Already on page {target_page}")
                                return True
                            
                            # Scroll to button and click
                            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", button)
                            time.sleep(1)
                            
                            # Try multiple click methods
                            click_methods = [
                                lambda: button.click(),
                                lambda: driver.execute_script("arguments[0].click();", button),
                                lambda: ActionChains(driver).move_to_element(button).click().perform()
                            ]
                            
                            for method in click_methods:
                                try:
                                    method()
                                    logger.info(f"Successfully clicked page {target_page}")
                                    time.sleep(3)  # Wait for page to load
                                    return True
                                except Exception as e:
                                    logger.debug(f"Click method failed: {e}")
                                    continue
                            
                            logger.error(f"All click methods failed for page {target_page}")
                            return False
                            
                except Exception as e:
                    logger.debug(f"Error processing pagination button: {e}")
                    continue
            
            logger.warning(f"Page {target_page} button not found in pagination")
            return False
            
        except Exception as e:
            logger.error(f"Error clicking page number {target_page}: {e}")
            return False
    
    def scrape_single_page(self, base_url, page_number):
        """Scrape a single page in its own driver instance"""
        driver = None
        try:
            logger.info(f"Thread {threading.current_thread().name}: Starting page {page_number}")
            
            # Setup driver for this thread
            driver = self.setup_driver()
            if not driver:
                logger.error(f"Failed to setup driver for page {page_number}")
                return []
            
            # Navigate to the specific page
            if not self.navigate_to_page_by_url(driver, base_url, page_number):
                logger.error(f"Failed to navigate to page {page_number}")
                return []
            
            # Wait a bit more for content to fully load
            time.sleep(3)
            
            # Extract hotels from this page
            hotels = self.extract_hotels_from_page(driver, page_number)
            
            logger.info(f"Thread {threading.current_thread().name}: Extracted {len(hotels)} hotels from page {page_number}")
            return hotels
            
        except Exception as e:
            logger.error(f"Error scraping page {page_number}: {e}")
            return []
        finally:
            if driver:
                try:
                    driver.quit()
                except:
                    pass
    
    def extract_hotels_from_page(self, driver, page_number):
        """Extract hotel data from current page"""
        hotels = []
        
        try:
            # Find hotel elements using multiple selectors
            hotel_elements = self.find_hotel_elements(driver)
            
            if not hotel_elements:
                logger.warning(f"No hotel elements found on page {page_number}")
                # Try waiting a bit more and retry
                time.sleep(5)
                hotel_elements = self.find_hotel_elements(driver)
            
            if not hotel_elements:
                logger.error(f"Still no hotel elements found on page {page_number}")
                return hotels
            
            logger.info(f"Found {len(hotel_elements)} hotel elements on page {page_number}")
            
            for index, hotel_element in enumerate(hotel_elements):
                try:
                    hotel_data = self.extract_hotel_data(hotel_element, page_number, index + 1)
                    hotels.append(hotel_data)
                    
                except Exception as e:
                    logger.error(f"Error extracting hotel {index + 1} on page {page_number}: {e}")
                    continue
            
            return hotels
            
        except Exception as e:
            logger.error(f"Error extracting hotels from page {page_number}: {e}")
            return hotels
    
    def find_hotel_elements(self, driver):
        """Find hotel elements using multiple strategies"""
        hotel_selectors = [
            ".g3BCYF",  # Primary selector
            "[data-testid='item']",
            ".item",
            ".hotel-item",
            ".accommodation-item",
            ".search-result",
            "[class*='item-']",
            "[class*='hotel-']",
            "[class*='accommodation-']",
            "._1Wh5Tf",  # Alternative selector
            ".result-item",
            ".hotel-card",
            ".property-card"
        ]
        
        for selector in hotel_selectors:
            try:
                if selector.startswith(".") and "_" in selector:
                    # Handle class names with underscores
                    class_name = selector.replace(".", "")
                    elements = driver.find_elements(By.CLASS_NAME, class_name)
                else:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                
                if elements:
                    logger.info(f"Found {len(elements)} hotel elements with selector: {selector}")
                    return elements
                    
            except Exception as e:
                logger.debug(f"Error with selector {selector}: {e}")
                continue
        
        logger.warning("No hotel elements found with any selector")
        return []
    
    def extract_hotel_data(self, hotel_element, page_number, hotel_index):
        """Extract comprehensive hotel data"""
        hotel_data = {
            'hotel_index': f"P{page_number}H{hotel_index}",
            'hotel_name': 'N/A',
            'price': 'N/A',
            'rating': 'N/A',
            'location': 'N/A',
            'amenities': 'N/A',
            'reviews_count': 'N/A',
            'deal_type': 'N/A',
            'features': 'N/A',
            'page_number': page_number,
            'extraction_time': datetime.now().isoformat()
        }
        
        try:
            # Extract hotel name
            name_selectors = [
                ".name-link",
                "[data-testid='item-name']",
                ".item-name",
                "h3", "h2", "h1",
                ".hotel-name",
                "[class*='name']",
                "[class*='title']",
                "a[href*='hotel']",
                ".hotel-title"
            ]
            
            hotel_name = self.extract_text_by_selectors(hotel_element, name_selectors)
            if hotel_name:
                hotel_data['hotel_name'] = hotel_name
            
            # Extract price
            price_selectors = [
                ".price",
                "[data-testid='price']",
                ".item-price",
                "[class*='price']",
                "[class*='rate']",
                ".deal-price",
                ".rate-info",
                ".price-display",
                ".cost"
            ]
            
            price = self.extract_text_by_selectors(hotel_element, price_selectors)
            if price:
                hotel_data['price'] = price
            
            # Extract rating
            rating_selectors = [
                ".rating",
                "[data-testid='rating']",
                ".item-rating",
                "[class*='rating']",
                "[class*='star']",
                ".review-score",
                ".stars",
                ".score"
            ]
            
            rating = self.extract_text_by_selectors(hotel_element, rating_selectors)
            if rating:
                hotel_data['rating'] = rating
            
            # Extract location
            location_selectors = [
                ".location",
                "[data-testid='location']",
                ".item-location",
                "[class*='location']",
                "[class*='address']",
                ".accommodation-location",
                ".distance",
                ".area",
                ".neighborhood"
            ]
            
            location = self.extract_text_by_selectors(hotel_element, location_selectors)
            if location:
                hotel_data['location'] = location
            
            # Extract reviews count
            reviews_selectors = [
                ".reviews",
                "[data-testid='reviews']",
                ".review-count",
                "[class*='review']",
                ".rating-count",
                ".review-number"
            ]
            
            reviews = self.extract_text_by_selectors(hotel_element, reviews_selectors)
            if reviews:
                hotel_data['reviews_count'] = reviews
            
            # Extract deal type
            deal_selectors = [
                ".deal-type",
                ".offer-type",
                "[class*='deal']",
                "[class*='offer']",
                ".promotion",
                ".special-offer"
            ]
            
            deal = self.extract_text_by_selectors(hotel_element, deal_selectors)
            if deal:
                hotel_data['deal_type'] = deal
            
            # Extract amenities
            amenity_selectors = [
                ".amenities",
                ".features",
                "[class*='amenity']",
                "[class*='feature']",
                ".facilities",
                "[class*='facility']",
                ".services"
            ]
            
            amenities = self.extract_text_by_selectors(hotel_element, amenity_selectors)
            if amenities:
                hotel_data['amenities'] = amenities
            
            # Extract features
            features_selectors = [
                ".hotel-features",
                "[class*='feature']",
                ".property-features",
                "[class*='highlight']",
                ".highlights",
                ".benefits"
            ]
            
            features = self.extract_text_by_selectors(hotel_element, features_selectors)
            if features:
                hotel_data['features'] = features
            
            # Parse additional info from all text
            try:
                all_text = hotel_element.text
                if all_text:
                    # Parse price patterns
                    if hotel_data['price'] == 'N/A':
                        price_patterns = [
                            r'[₹$€£]\s*[\d,]+(?:\.\d{2})?',
                            r'Rs\.?\s*[\d,]+(?:\.\d{2})?',
                            r'INR\s*[\d,]+(?:\.\d{2})?',
                            r'[\d,]+(?:\.\d{2})?\s*per\s*night',
                            r'[\d,]+(?:\.\d{2})?\s*(?:₹|Rs|INR)'
                        ]
                        for pattern in price_patterns:
                            match = re.search(pattern, all_text, re.IGNORECASE)
                            if match:
                                hotel_data['price'] = match.group()
                                break
                    
                    # Parse rating patterns
                    if hotel_data['rating'] == 'N/A':
                        rating_patterns = [
                            r'(\d+\.?\d*)\s*(?:stars?|★|/10|/5)',
                            r'(\d+\.?\d*)\s*rating',
                            r'(\d+\.?\d*)\s*out\s*of\s*[5|10]',
                            r'(\d+\.?\d*)\s*\/\s*[5|10]'
                        ]
                        for pattern in rating_patterns:
                            match = re.search(pattern, all_text, re.IGNORECASE)
                            if match:
                                hotel_data['rating'] = match.group(1)
                                break
                    
                    # Parse review count
                    if hotel_data['reviews_count'] == 'N/A':
                        review_patterns = [
                            r'(\d+)\s*(?:reviews?|ratings?)',
                            r'(\d+)\s*guest\s*reviews?',
                            r'Based\s*on\s*(\d+)\s*reviews?',
                            r'(\d+)\s*review',
                            r'(\d+)\s*people\s*reviewed'
                        ]
                        for pattern in review_patterns:
                            match = re.search(pattern, all_text, re.IGNORECASE)
                            if match:
                                hotel_data['reviews_count'] = match.group(1)
                                break
                        
            except Exception as e:
                logger.debug(f"Error parsing additional text: {e}")
            
            return hotel_data
            
        except Exception as e:
            logger.error(f"Error extracting hotel data: {e}")
            return hotel_data
    
    def extract_text_by_selectors(self, parent_element, selectors):
        """Try multiple selectors to extract text"""
        for selector in selectors:
            try:
                elements = parent_element.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    text = elements[0].text.strip()
                    if text:
                        return text
            except Exception as e:
                logger.debug(f"Selector {selector} failed: {e}")
                continue
        return None
    
    def scrape_all_pages_parallel(self, base_url):
        """Main scraping function with true parallel processing"""
        logger.info(f"Starting parallel scraping of all {self.total_pages} pages")
        
        # Create a list of all page numbers to scrape
        pages_to_scrape = list(range(1, self.total_pages + 1))
        
        # Use ThreadPoolExecutor for parallel processing
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks simultaneously
            future_to_page = {
                executor.submit(self.scrape_single_page, base_url, page_num): page_num
                for page_num in pages_to_scrape
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_page):
                page_num = future_to_page[future]
                try:
                    hotels = future.result()
                    
                    # Thread-safe addition to results
                    with self.data_lock:
                        self.hotels_data.extend(hotels)
                    
                    logger.info(f"✓ Completed page {page_num}: {len(hotels)} hotels")
                    
                except Exception as e:
                    logger.error(f"✗ Error processing page {page_num}: {e}")
        
        logger.info(f"Parallel scraping completed. Total hotels: {len(self.hotels_data)}")
        return True
    
    def save_to_csv(self):
        """Save extracted hotel data to CSV file"""
        if not self.hotels_data:
            logger.warning("No hotel data to save")
            return
        
        try:
            # Sort by page number and hotel index
            self.hotels_data.sort(key=lambda x: (x['page_number'], x['hotel_index']))
            
            df = pd.DataFrame(self.hotels_data)
            filename = f"trivago_hotels_improved_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            df.to_csv(filename, index=False, encoding='utf-8')
            
            logger.info(f"Saved {len(self.hotels_data)} hotels to {filename}")
            
            # Print detailed summary
            print(f"\n{'='*70}")
            print(f"IMPROVED PARALLEL SCRAPING SUMMARY")
            print(f"{'='*70}")
            print(f"Total hotels extracted: {len(self.hotels_data)}")
            print(f"Total pages scraped: {len(set(h['page_number'] for h in self.hotels_data))}")
            print(f"Pages with data: {sorted(set(h['page_number'] for h in self.hotels_data))}")
            
            # Data quality metrics
            print(f"\nData Quality Metrics:")
            print(f"Hotels with names: {len([h for h in self.hotels_data if h['hotel_name'] != 'N/A'])}")
            print(f"Hotels with prices: {len([h for h in self.hotels_data if h['price'] != 'N/A'])}")
            print(f"Hotels with ratings: {len([h for h in self.hotels_data if h['rating'] != 'N/A'])}")
            print(f"Hotels with locations: {len([h for h in self.hotels_data if h['location'] != 'N/A'])}")
            print(f"Hotels with reviews: {len([h for h in self.hotels_data if h['reviews_count'] != 'N/A'])}")
            
            # Per-page breakdown
            print(f"\nPer-Page Breakdown:")
            for page_num in sorted(set(h['page_number'] for h in self.hotels_data)):
                page_hotels = [h for h in self.hotels_data if h['page_number'] == page_num]
                print(f"Page {page_num:2d}: {len(page_hotels):2d} hotels")
            
            print(f"\nData saved to: {filename}")
            
            # Show sample data
            print(f"\nSample Hotels (first 3):")
            for i, hotel in enumerate(self.hotels_data[:3]):
                print(f"\n{i+1}. {hotel['hotel_name']}")
                print(f"   Price: {hotel['price']}")
                print(f"   Rating: {hotel['rating']}")
                print(f"   Location: {hotel['location']}")
                print(f"   Page: {hotel['page_number']}")
                print(f"   Reviews: {hotel['reviews_count']}")
            
        except Exception as e:
            logger.error(f"Error saving to CSV: {e}")

def main():
    """Main function"""
    url = "https://www.trivago.in/en-IN/lm/hotels-darjeeling-india?search=200-80950;dr-20250721-20250722#"
    
    # Create scraper with improved parallel processing
    scraper = TrivagoImprovedScraper(
        headless=False,  # Set to True for faster scraping
        max_workers=5    # Increased workers for true parallel processing
    )
    
    logger.info("Starting Trivago IMPROVED parallel scraper...")
    logger.info(f"Will scrape {scraper.total_pages} pages using {scraper.max_workers} parallel workers")
    logger.info("Each page will open in its own browser instance simultaneously")
    
    start_time = time.time()
    
    success = scraper.scrape_all_pages_parallel(url)
    
    end_time = time.time()
    duration = end_time - start_time
    
    if success:
        scraper.save_to_csv()
        logger.info(f"✓ Scraping completed successfully in {duration:.2f} seconds!")
        logger.info(f"Average time per page: {duration/scraper.total_pages:.2f} seconds")
        logger.info(f"Efficiency improvement: True parallel processing of all {scraper.total_pages} pages")
    else:
        logger.error("✗ Scraping failed!")

if __name__ == "__main__":
    main()