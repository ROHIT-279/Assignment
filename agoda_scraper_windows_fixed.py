from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException
import time
import csv
import json
from datetime import datetime
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
import re
import os
import sys

# Fix encoding for Windows
if sys.platform.startswith('win'):
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.detach())
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.detach())

# Setup logging with ASCII-safe messages for Windows compatibility
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('agoda_scraper.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class AgodaScraperWindowsFixed:
    def __init__(self, max_workers=5):
        self.max_workers = max_workers
        self.hotel_data = []
        self.processed_urls = set()
        
    def setup_driver(self, headless=True):
        """Setup Firefox driver with optimized options for Windows"""
        options = Options()
        if headless:
            options.add_argument("--headless")
        
        # Windows-specific optimizations
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
        
        # Memory optimizations
        options.add_argument("--memory-pressure-off")
        options.add_argument("--disable-background-timer-throttling")
        options.add_argument("--disable-renderer-backgrounding")
        
        try:
            driver = webdriver.Firefox(options=options)
            driver.set_page_load_timeout(30)
            driver.implicitly_wait(10)
            return driver
        except Exception as e:
            logger.error(f"Error setting up driver: {e}")
            raise
            
    def extract_hotel_urls(self, search_url):
        """Extract hotel URLs from search results with improved selectors"""
        driver = self.setup_driver(headless=True)
        hotel_urls = set()
        
        try:
            logger.info("Starting Phase 1: Extracting hotel URLs...")
            driver.get(search_url)
            
            # Wait for page to load
            logger.info("Loading search results page...")
            time.sleep(10)
            
            # Multiple CSS selectors to try for hotel items
            hotel_selectors = [
                'li[data-selenium="hotel-item"]',
                '[data-selenium="hotel-item"]',
                '.PropertyCard',
                '.hotel-item',
                '.property-card',
                '[data-testid="property-card"]',
                '.PropertyCardWrapper',
                '.property-list-item'
            ]
            
            page_num = 1
            scroll_count = 0
            max_scrolls = 20
            
            while scroll_count < max_scrolls:
                # Try different selectors to find hotels
                hotels_found = 0
                page_source = driver.page_source
                soup = BeautifulSoup(page_source, 'html.parser')
                
                for selector in hotel_selectors:
                    hotel_elements = soup.select(selector)
                    if hotel_elements:
                        logger.info(f"Found {len(hotel_elements)} hotels using selector: {selector}")
                        
                        for hotel in hotel_elements:
                            # Try different ways to extract hotel URLs
                            url = None
                            
                            # Method 1: Look for direct links
                            link = hotel.find('a', href=True)
                            if link:
                                url = link['href']
                            
                            # Method 2: Look for data attributes
                            if not url:
                                url = hotel.get('data-href') or hotel.get('data-url')
                            
                            # Method 3: Look within nested elements
                            if not url:
                                nested_link = hotel.find('a', {'data-selenium': 'hotel-link'})
                                if nested_link:
                                    url = nested_link.get('href')
                            
                            if url:
                                # Ensure absolute URL
                                if url.startswith('/'):
                                    url = f"https://www.agoda.com{url}"
                                elif not url.startswith('http'):
                                    url = f"https://www.agoda.com/{url}"
                                
                                if url not in hotel_urls:
                                    hotel_urls.add(url)
                                    hotels_found += 1
                        
                        if hotels_found > 0:
                            break  # Found hotels with this selector, no need to try others
                
                logger.info(f"Page {page_num}: Found {hotels_found} new hotels (Total: {len(hotel_urls)})")
                
                if hotels_found == 0:
                    # Debug: Save page source to check structure
                    with open(f'debug_page_{page_num}.html', 'w', encoding='utf-8') as f:
                        f.write(page_source)
                    logger.warning(f"No hotels found on page {page_num}. Debug file saved.")
                
                # Scroll down to load more content
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight * 0.8);")
                time.sleep(3)
                
                # Try to click "Load More" or "Next Page" button
                try:
                    # Multiple possible pagination selectors
                    pagination_selectors = [
                        'button[data-selenium="pagination-next-btn"]',
                        '.pagination-next',
                        '[data-testid="pagination-next"]',
                        '.next-page',
                        'button[aria-label="Next page"]',
                        '.paging-next'
                    ]
                    
                    clicked = False
                    for selector in pagination_selectors:
                        try:
                            next_button = driver.find_element(By.CSS_SELECTOR, selector)
                            if next_button.is_enabled():
                                driver.execute_script("arguments[0].click();", next_button)
                                time.sleep(5)
                                page_num += 1
                                clicked = True
                                break
                        except:
                            continue
                    
                    if not clicked:
                        # Try scrolling more to trigger infinite scroll
                        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                        time.sleep(3)
                        scroll_count += 1
                    else:
                        scroll_count = 0  # Reset scroll count if we successfully paginated
                        
                except Exception as e:
                    logger.debug(f"Pagination failed: {e}")
                    scroll_count += 1
                
                # If no new hotels found for several attempts, break
                if hotels_found == 0:
                    scroll_count += 1
            
            logger.info("No more pages or pagination failed")
            logger.info(f"Total hotels found: {len(hotel_urls)}, Total scrolls: {scroll_count}")
            
        except Exception as e:
            logger.error(f"Error extracting hotel URLs: {e}")
        finally:
            driver.quit()
        
        return list(hotel_urls)
    
    def extract_hotel_data(self, hotel_url, worker_id=0):
        """Extract detailed data from a single hotel page"""
        driver = self.setup_driver(headless=True)
        hotel_data = []
        
        try:
            logger.info(f"Worker {worker_id}: Processing {hotel_url[:100]}...")
            driver.get(hotel_url)
            time.sleep(5)
            
            # Wait for content to load
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            
            # Extract hotel name
            hotel_name = "Unknown Hotel"
            name_selectors = [
                'h1[data-selenium="hotel-header-name"]',
                'h1.hotel-name',
                '.hotel-header-name',
                'h1',
                '.property-name'
            ]
            
            for selector in name_selectors:
                name_element = soup.select_one(selector)
                if name_element:
                    hotel_name = name_element.get_text(strip=True)
                    break
            
            # Extract overall rating
            overall_rating = "N/A"
            rating_selectors = [
                '.review-score',
                '.rating-score',
                '[data-selenium="hotel-review-score"]',
                '.overall-rating'
            ]
            
            for selector in rating_selectors:
                rating_element = soup.select_one(selector)
                if rating_element:
                    overall_rating = rating_element.get_text(strip=True)
                    break
            
            # Extract room prices
            room_prices = []
            price_selectors = [
                '.room-price',
                '.price-display',
                '[data-selenium="room-price"]',
                '.rate-price'
            ]
            
            for selector in price_selectors:
                price_elements = soup.select(selector)
                for price_elem in price_elements:
                    price_text = price_elem.get_text(strip=True)
                    # Extract numeric price
                    price_match = re.search(r'[\d,]+', price_text)
                    if price_match:
                        room_prices.append(price_match.group())
            
            # If no prices found, try alternative approach
            if not room_prices:
                # Look for any text containing currency symbols
                price_patterns = [r'₹\s*[\d,]+', r'INR\s*[\d,]+', r'\$\s*[\d,]+']
                page_text = soup.get_text()
                for pattern in price_patterns:
                    matches = re.findall(pattern, page_text)
                    for match in matches:
                        price_num = re.search(r'[\d,]+', match)
                        if price_num:
                            room_prices.append(price_num.group())
            
            # Create records for each room price or at least one record
            if room_prices:
                for price in room_prices[:10]:  # Limit to first 10 prices
                    hotel_data.append({
                        'hotel_name': hotel_name,
                        'hotel_url': hotel_url,
                        'overall_rating': overall_rating,
                        'extraction_timestamp': datetime.now().isoformat(),
                        'room_category': '',
                        'room_price': price,
                        'reviewer_info': '',
                        'room_type_reviewed': '',
                        'review_rating': '',
                        'review_date': '',
                        'review_comment': ''
                    })
            else:
                # Create at least one record even without price
                hotel_data.append({
                    'hotel_name': hotel_name,
                    'hotel_url': hotel_url,
                    'overall_rating': overall_rating,
                    'extraction_timestamp': datetime.now().isoformat(),
                    'room_category': '',
                    'room_price': 'N/A',
                    'reviewer_info': '',
                    'room_type_reviewed': '',
                    'review_rating': '',
                    'review_date': '',
                    'review_comment': ''
                })
            
            logger.info(f"Worker {worker_id}: Successfully extracted data for {hotel_name}")
            
        except Exception as e:
            logger.error(f"Worker {worker_id}: Error processing {hotel_url}: {e}")
            # Create minimal record for failed extraction
            hotel_data.append({
                'hotel_name': 'Extraction Failed',
                'hotel_url': hotel_url,
                'overall_rating': 'N/A',
                'extraction_timestamp': datetime.now().isoformat(),
                'room_category': '',
                'room_price': 'N/A',
                'reviewer_info': '',
                'room_type_reviewed': '',
                'review_rating': '',
                'review_date': '',
                'review_comment': ''
            })
        finally:
            driver.quit()
        
        return hotel_data
    
    def save_to_csv(self, data, filename):
        """Save data to CSV file with Windows-compatible encoding"""
        try:
            with open(filename, 'w', newline='', encoding='utf-8-sig') as csvfile:
                if data:
                    fieldnames = data[0].keys()
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(data)
                    logger.info(f"Data saved to {filename}")
                else:
                    logger.warning("No data to save")
        except Exception as e:
            logger.error(f"Error saving CSV: {e}")
    
    def save_to_json(self, data, filename):
        """Save data to JSON file"""
        try:
            with open(filename, 'w', encoding='utf-8') as jsonfile:
                json.dump(data, jsonfile, indent=2, ensure_ascii=False)
                logger.info(f"Raw data saved to {filename}")
        except Exception as e:
            logger.error(f"Error saving JSON: {e}")
    
    def process_hotels_batch(self, hotel_urls, batch_num):
        """Process a batch of hotels using multi-threading"""
        logger.info(f"Processing batch {batch_num} with {len(hotel_urls)} hotels")
        batch_data = []
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit tasks
            future_to_url = {
                executor.submit(self.extract_hotel_data, url, f"{batch_num}-{i}"): url 
                for i, url in enumerate(hotel_urls)
            }
            
            # Collect results
            for future in as_completed(future_to_url):
                url = future_to_url[future]
                try:
                    hotel_data = future.result()
                    batch_data.extend(hotel_data)
                    hotel_name = hotel_data[0]['hotel_name'] if hotel_data else 'Unknown'
                    logger.info(f"Completed: {hotel_name}")
                except Exception as exc:
                    logger.error(f"Hotel {url} generated an exception: {exc}")
        
        # Save batch results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        batch_filename = f"agoda_batch_{batch_num}_{timestamp}.csv"
        self.save_to_csv(batch_data, batch_filename)
        logger.info(f"Batch {batch_num} saved to {batch_filename}")
        
        return batch_data
    
    def run_scraper(self, search_url, max_hotels=None):
        """Main scraper function"""
        start_time = datetime.now()
        logger.info(f"Starting Agoda scraper at {start_time}")
        
        # Phase 1: Extract hotel URLs
        logger.info("Phase 1: Extracting hotel URLs...")
        hotel_urls = self.extract_hotel_urls(search_url)
        
        if not hotel_urls:
            logger.error("No hotel URLs found")
            logger.info("This might be due to:")
            logger.info("1. Website structure changes")
            logger.info("2. Anti-bot measures")
            logger.info("3. Invalid search URL")
            logger.info("4. Network connectivity issues")
            return
        
        logger.info(f"Found {len(hotel_urls)} hotels to process")
        
        # Limit hotels if specified
        if max_hotels:
            hotel_urls = hotel_urls[:max_hotels]
            logger.info(f"Limited to {max_hotels} hotels")
        
        # Phase 2: Process hotels in batches
        batch_size = 5
        all_data = []
        
        for i in range(0, len(hotel_urls), batch_size):
            batch_num = (i // batch_size) + 1
            batch_urls = hotel_urls[i:i + batch_size]
            
            logger.info(f"Processing batch {batch_num}/{(len(hotel_urls) + batch_size - 1) // batch_size}")
            
            batch_data = self.process_hotels_batch(batch_urls, batch_num)
            all_data.extend(batch_data)
        
        # Save final results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        final_filename = f"agoda_hotels_final_{timestamp}.csv"
        json_filename = f"agoda_raw_data_{timestamp}.json"
        
        self.save_to_csv(all_data, final_filename)
        self.save_to_json(all_data, json_filename)
        
        # Summary
        end_time = datetime.now()
        duration = end_time - start_time
        
        logger.info("Scraping completed!")
        logger.info(f"Total hotels processed: {len(set(item['hotel_name'] for item in all_data))}")
        logger.info(f"Total records created: {len(all_data)}")
        logger.info(f"Total time: {duration}")
        logger.info(f"Final output: {final_filename}")

def main():
    # Your Agoda search URL
    search_url = "https://www.agoda.com/en-in/search?guid=ac34b805-fbbb-4a54-91f6-72bd44251297&asq=oSBZUdCJkTqIcAJrG1AX8Jufa9Vwpz6XltTHq4n%2B9gNpSLc%2BT%2BpB%2F8FnmmA8sOyAJ0WZY5hpLWEr%2Fk8qr78gW4DMS7e7llLtqq76yKsoLJ2OoQ3gw8ln%2FUAwfEcSpHO4IoT8r2EKxXsqX%2FNiA5fxsgqQMycviD3CIWSJVwpQ8sqLB7kVtS1F64bq7yiJpY541pwsBzifP5NpR6wrJ1u54kHb%2BKC2e3zym6tmyvlzCzM%3D&city=10863&tick=638881978745&locale=en-in&ckuid=0782016a-40d3-4e7a-86a4-8cab9dacec41&prid=0&gclid=Cj0KCQjw-NfDBhDyARIsAD-ILeBXva5TJhq-jGK3Si0BOfvtLo82iIstmv4-XMoqfU56Mshxz_UezUkaAhwMEALw_wcB&currency=INR&correlationId=55168ae7-8bc1-4224-a8eb-86ba246be729&analyticsSessionId=-1950121884218971931&pageTypeId=1&realLanguageId=15&languageId=1&origin=IN&stateCode=WB&cid=1922885&tag=6f147157-60b8-459f-af1a-9935d44970e9&userId=0782016a-40d3-4e7a-86a4-8cab9dacec41&whitelabelid=1&loginLvl=0&storefrontId=3&currencyId=27&currencyCode=INR&htmlLanguage=en-in&cultureInfoName=en-in&machineName=sg-pc-6h-acm-web-user-8697c4cd7c-gmgqx&trafficGroupId=5&trafficSubGroupId=122&aid=82361&useFullPageLogin=true&cttp=4&isRealUser=true&mode=production&browserFamily=Chrome&cdnDomain=agoda.net&checkIn=2025-08-12&checkOut=2025-08-13&rooms=1&adults=2&children=0&priceCur=INR&los=1&textToSearch=Darjeeling&travellerType=1&familyMode=off&ds=cgN73pCK5wrspJ7h&productType=-1"
    
    # Create scraper instance
    scraper = AgodaScraperWindowsFixed(max_workers=5)
    
    # Run scraper
    scraper.run_scraper(search_url, max_hotels=25)

if __name__ == "__main__":
    main()