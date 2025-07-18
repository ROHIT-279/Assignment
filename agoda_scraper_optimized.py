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

# Setup logging
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('agoda_scraper.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class AgodaScraperOptimized:
    def __init__(self, max_workers=5):
        self.max_workers = max_workers
        self.hotel_data = []
        self.processed_urls = set()
        
    def setup_driver(self, headless=True):
        """Setup Firefox driver with optimized options"""
        options = Options()
        if headless:
            options.add_argument("--headless")
        
        # Performance optimizations
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-images")
        options.add_argument("--disable-javascript")  # Will re-enable if needed
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
        
        # Memory optimizations
        options.set_preference("dom.webdriver.enabled", False)
        options.set_preference("useAutomationExtension", False)
        options.set_preference("general.useragent.override", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        
        try:
            driver = webdriver.Firefox(options=options)
            driver.implicitly_wait(10)
            driver.set_page_load_timeout(30)
            return driver
        except Exception as e:
            logger.error(f"Failed to setup driver: {e}")
            raise

    def extract_hotel_urls(self, search_url):
        """Extract hotel URLs from search results with improved scrolling"""
        driver = self.setup_driver(headless=False)  # Keep visible for initial scraping
        hotel_urls = []
        
        try:
            logger.info("Loading search results page...")
            driver.get(search_url)
            
            # Wait for hotels to load
            WebDriverWait(driver, 20).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'li[data-selenium="hotel-item"]'))
            )
            
            page_count = 0
            max_pages = 10  # Limit to prevent infinite scrolling
            scroll_count = 0
            
            while page_count < max_pages:
                try:
                    # Progressive scrolling to load all hotels on current page
                    last_height = driver.execute_script("return document.body.scrollHeight")
                    
                    # Scroll down in increments
                    for i in range(0, 100, 20):
                        driver.execute_script(f"window.scrollTo(0, document.body.scrollHeight * {i/100});")
                        time.sleep(1)
                        scroll_count += 1
                    
                    # Wait for any lazy loading
                    time.sleep(3)
                    
                    # Extract hotel URLs from current page
                    soup = BeautifulSoup(driver.page_source, "html.parser")
                    hotel_elements = soup.select('li[data-selenium="hotel-item"]')
                    
                    page_hotels = 0
                    for hotel in hotel_elements:
                        # Use your specified selector
                        hotel_link = hotel.find('a', {'data-testid': 'property-name-link'})
                        if hotel_link and hotel_link.get('href'):
                            full_url = "https://www.agoda.com" + hotel_link.get('href')
                            if full_url not in hotel_urls:
                                hotel_urls.append(full_url)
                                page_hotels += 1
                    
                    logger.info(f"Page {page_count + 1}: Found {page_hotels} new hotels (Total: {len(hotel_urls)})")
                    
                    # Try to go to next page
                    try:
                        next_button = WebDriverWait(driver, 5).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[data-selenium="pagination-next-btn"]'))
                        )
                        
                        if next_button.is_enabled():
                            # Scroll to button and click
                            driver.execute_script("arguments[0].scrollIntoView(true);", next_button)
                            time.sleep(1)
                            next_button.click()
                            
                            # Wait for new page to load
                            WebDriverWait(driver, 15).until(
                                EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'li[data-selenium="hotel-item"]'))
                            )
                            time.sleep(3)
                            page_count += 1
                        else:
                            logger.info("Next button disabled, reached last page")
                            break
                            
                    except (TimeoutException, NoSuchElementException, ElementClickInterceptedException):
                        logger.info("No more pages or pagination failed")
                        break
                        
                except Exception as e:
                    logger.error(f"Error on page {page_count}: {e}")
                    break
            
            logger.info(f"Total hotels found: {len(hotel_urls)}, Total scrolls: {scroll_count}")
            
        except Exception as e:
            logger.error(f"Error extracting hotel URLs: {e}")
        finally:
            driver.quit()
            
        return hotel_urls

    def extract_hotel_details(self, hotel_url, worker_id):
        """Extract detailed hotel information using your specified selectors"""
        driver = self.setup_driver(headless=True)
        
        hotel_data = {
            'hotel_url': hotel_url,
            'hotel_name': '',
            'overall_rating': '',
            'room_categories': [],
            'reviews': [],
            'worker_id': worker_id,
            'extraction_timestamp': datetime.now().isoformat()
        }
        
        try:
            logger.info(f"Worker {worker_id}: Processing {hotel_url}")
            driver.get(hotel_url)
            
            # Wait for page to load
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            time.sleep(3)
            
            soup = BeautifulSoup(driver.page_source, "html.parser")
            
            # Extract hotel name
            hotel_name_candidates = [
                soup.find('h1'),
                soup.find('h1', class_=lambda x: x and 'hotel' in x.lower()),
                soup.find('div', class_=lambda x: x and 'property-name' in x.lower()),
            ]
            
            for candidate in hotel_name_candidates:
                if candidate and candidate.get_text(strip=True):
                    hotel_data['hotel_name'] = candidate.get_text(strip=True)
                    break
            
            # Extract overall rating
            rating_selectors = [
                'div[class*="rating"]',
                'span[class*="rating"]',
                'div[class*="score"]',
                '.review-score',
                '[data-testid*="rating"]'
            ]
            
            for selector in rating_selectors:
                rating_elem = soup.select_one(selector)
                if rating_elem and rating_elem.get_text(strip=True):
                    hotel_data['overall_rating'] = rating_elem.get_text(strip=True)
                    break
            
            # Extract room categories and prices using your selector
            room_elements = soup.find_all('div', class_=lambda x: x and 'cor-tooltip-wrapper' in x)
            
            for room_elem in room_elements:
                room_info = {'category': '', 'price': ''}
                
                # Extract room category using your selector
                category_elem = room_elem.find('div', {'data-info-type': 'room-type'})
                if category_elem:
                    room_info['category'] = category_elem.get_text(strip=True)
                
                # Extract price
                price_selectors = [
                    'span[class*="price"]',
                    'div[class*="price"]',
                    '[data-testid*="price"]',
                    '.price'
                ]
                
                for price_selector in price_selectors:
                    price_elem = room_elem.select_one(price_selector)
                    if price_elem:
                        price_text = price_elem.get_text(strip=True)
                        if price_text and any(char.isdigit() for char in price_text):
                            room_info['price'] = price_text
                            break
                
                if room_info['category'] or room_info['price']:
                    hotel_data['room_categories'].append(room_info)
            
            # Extract reviews
            self.extract_reviews(driver, soup, hotel_data)
            
            logger.info(f"Worker {worker_id}: Successfully extracted data for {hotel_data['hotel_name']}")
            
        except Exception as e:
            logger.error(f"Worker {worker_id}: Error extracting details from {hotel_url}: {e}")
        finally:
            driver.quit()
            
        return hotel_data

    def extract_reviews(self, driver, soup, hotel_data):
        """Extract reviews using your specified selectors"""
        try:
            # Try to find and click reviews link
            reviews_link_selectors = [
                'a[href*="reviews"]',
                'button[data-testid*="reviews"]',
                '.reviews-link',
                '[data-selenium*="reviews"]'
            ]
            
            reviews_clicked = False
            for selector in reviews_link_selectors:
                try:
                    reviews_link = driver.find_element(By.CSS_SELECTOR, selector)
                    driver.execute_script("arguments[0].scrollIntoView(true);", reviews_link)
                    time.sleep(1)
                    reviews_link.click()
                    time.sleep(3)
                    reviews_clicked = True
                    break
                except:
                    continue
            
            if reviews_clicked:
                soup = BeautifulSoup(driver.page_source, "html.parser")
            
            # Extract reviews using your selectors
            review_sections = soup.find_all('div', class_=lambda x: x and any(cls in x for cls in ['af0e5-box', 'Review-comment-bubble']))
            
            if not review_sections:
                # Alternative review selectors
                review_sections = soup.find_all('div', class_=lambda x: x and 'review' in x.lower())
            
            for review_section in review_sections[:15]:  # Limit to 15 reviews
                review_data = {
                    'reviewer_info': '',
                    'room_type': '',
                    'rating': '',
                    'date': '',
                    'comment': ''
                }
                
                # Extract reviewer info using your selector
                reviewer_elem = review_section.find('div', class_=lambda x: x and 'Review-comment-reviewer' in x)
                if reviewer_elem:
                    review_data['reviewer_info'] = reviewer_elem.get_text(strip=True)
                
                # Extract room type using your selector
                room_type_elem = review_section.find('div', {'data-info-type': 'room-type'})
                if room_type_elem:
                    review_data['room_type'] = room_type_elem.get_text(strip=True)
                
                # Extract rating using your selector
                rating_elem = review_section.find('div', class_=lambda x: x and 'Review-comment-leftScore' in x)
                if rating_elem:
                    review_data['rating'] = rating_elem.get_text(strip=True)
                
                # Extract date using your selector
                date_elem = review_section.find('div', class_=lambda x: x and 'Typography' in x and 'sc-hKgILt' in x)
                if date_elem:
                    review_data['date'] = date_elem.get_text(strip=True)
                
                # Extract comment
                comment_elem = review_section.find('div', class_=lambda x: x and 'Review-comment-left' in x)
                if comment_elem:
                    review_data['comment'] = comment_elem.get_text(strip=True)
                
                # Only add if we have substantial data
                if any([review_data['rating'], review_data['comment'], review_data['date']]):
                    hotel_data['reviews'].append(review_data)
            
        except Exception as e:
            logger.warning(f"Could not extract reviews: {e}")

    def process_hotels_batch(self, hotel_urls_batch, batch_num):
        """Process a batch of hotels with improved error handling"""
        batch_results = []
        
        logger.info(f"Starting batch {batch_num} with {len(hotel_urls_batch)} hotels")
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit tasks
            future_to_url = {
                executor.submit(self.extract_hotel_details, url, f"{batch_num}-{i}"): url 
                for i, url in enumerate(hotel_urls_batch)
            }
            
            # Collect results with timeout
            for future in as_completed(future_to_url, timeout=300):  # 5 minute timeout per hotel
                url = future_to_url[future]
                try:
                    result = future.result(timeout=60)  # 1 minute timeout for result
                    if result and result['hotel_name']:
                        batch_results.append(result)
                        self.processed_urls.add(url)
                        logger.info(f"✓ Completed: {result['hotel_name']}")
                    else:
                        logger.warning(f"✗ No data extracted for: {url}")
                except Exception as e:
                    logger.error(f"✗ Error processing {url}: {e}")
        
        return batch_results

    def save_to_csv(self, filename="agoda_hotels_detailed.csv"):
        """Save data to CSV with improved structure"""
        if not self.hotel_data:
            logger.warning("No data to save")
            return
        
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = [
                'hotel_name', 'hotel_url', 'overall_rating', 'extraction_timestamp',
                'room_category', 'room_price', 'reviewer_info', 'room_type_reviewed',
                'review_rating', 'review_date', 'review_comment'
            ]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for hotel in self.hotel_data:
                # Create rows for each combination of room category and review
                room_categories = hotel['room_categories'] if hotel['room_categories'] else [{'category': '', 'price': ''}]
                reviews = hotel['reviews'] if hotel['reviews'] else [{'reviewer_info': '', 'room_type': '', 'rating': '', 'date': '', 'comment': ''}]
                
                for room in room_categories:
                    for review in reviews:
                        writer.writerow({
                            'hotel_name': hotel['hotel_name'],
                            'hotel_url': hotel['hotel_url'],
                            'overall_rating': hotel['overall_rating'],
                            'extraction_timestamp': hotel.get('extraction_timestamp', ''),
                            'room_category': room['category'],
                            'room_price': room['price'],
                            'reviewer_info': review['reviewer_info'],
                            'room_type_reviewed': review.get('room_type', ''),
                            'review_rating': review['rating'],
                            'review_date': review['date'],
                            'review_comment': review['comment']
                        })
        
        logger.info(f"✓ Data saved to {filename}")

    def run_scraper(self, search_url, max_hotels=None):
        """Main scraping orchestrator"""
        start_time = datetime.now()
        logger.info(f"🚀 Starting Agoda scraper at {start_time}")
        
        # Step 1: Extract hotel URLs
        logger.info("📋 Phase 1: Extracting hotel URLs...")
        hotel_urls = self.extract_hotel_urls(search_url)
        
        if not hotel_urls:
            logger.error("❌ No hotel URLs found")
            return
        
        if max_hotels:
            hotel_urls = hotel_urls[:max_hotels]
        
        logger.info(f"📊 Found {len(hotel_urls)} hotels to process")
        
        # Step 2: Process in batches
        batch_size = 5
        total_batches = (len(hotel_urls) + batch_size - 1) // batch_size
        
        for i in range(0, len(hotel_urls), batch_size):
            batch_num = (i // batch_size) + 1
            batch_urls = hotel_urls[i:i + batch_size]
            
            logger.info(f"🔄 Processing batch {batch_num}/{total_batches}")
            
            batch_results = self.process_hotels_batch(batch_urls, batch_num)
            self.hotel_data.extend(batch_results)
            
            # Save intermediate results
            if batch_results:
                intermediate_filename = f"agoda_batch_{batch_num}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                temp_data = self.hotel_data[-len(batch_results):]
                with open(intermediate_filename, 'w', newline='', encoding='utf-8') as csvfile:
                    fieldnames = [
                        'hotel_name', 'hotel_url', 'overall_rating', 'extraction_timestamp',
                        'room_category', 'room_price', 'reviewer_info', 'room_type_reviewed',
                        'review_rating', 'review_date', 'review_comment'
                    ]
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    writer.writeheader()
                    
                    for hotel in temp_data:
                        room_categories = hotel['room_categories'] if hotel['room_categories'] else [{'category': '', 'price': ''}]
                        reviews = hotel['reviews'] if hotel['reviews'] else [{'reviewer_info': '', 'room_type': '', 'rating': '', 'date': '', 'comment': ''}]
                        
                        for room in room_categories:
                            for review in reviews:
                                writer.writerow({
                                    'hotel_name': hotel['hotel_name'],
                                    'hotel_url': hotel['hotel_url'],
                                    'overall_rating': hotel['overall_rating'],
                                    'extraction_timestamp': hotel.get('extraction_timestamp', ''),
                                    'room_category': room['category'],
                                    'room_price': room['price'],
                                    'reviewer_info': review['reviewer_info'],
                                    'room_type_reviewed': review.get('room_type', ''),
                                    'review_rating': review['rating'],
                                    'review_date': review['date'],
                                    'review_comment': review['comment']
                                })
                
                logger.info(f"💾 Batch {batch_num} saved to {intermediate_filename}")
            
            # Brief pause between batches
            if i + batch_size < len(hotel_urls):
                logger.info("⏸️  Pausing 30 seconds between batches...")
                time.sleep(30)
        
        # Step 3: Save final results
        final_filename = f"agoda_hotels_final_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        self.save_to_csv(final_filename)
        
        # Save raw JSON backup
        json_filename = f"agoda_raw_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(json_filename, "w", encoding="utf-8") as f:
            json.dump(self.hotel_data, f, indent=2, ensure_ascii=False)
        
        end_time = datetime.now()
        duration = end_time - start_time
        
        logger.info(f"🎉 Scraping completed!")
        logger.info(f"📈 Total hotels processed: {len(self.hotel_data)}")
        logger.info(f"⏱️  Total time: {duration}")
        logger.info(f"📁 Final output: {final_filename}")

def main():
    # Your search URL
    search_url = "https://www.agoda.com/en-in/search?guid=ac34b805-fbbb-4a54-91f6-72bd44251297&asq=oSBZUdCJkTqIcAJrG1AX8Jufa9Vwpz6XltTHq4n%2B9gNpSLc%2BT%2BpB%2F8FnmmA8sOyAJ0WZY5hpLWEr%2Fk8qr78gW4DMS7e7llLtqq76yKsoLJ2OoQ3gw8ln%2FUAwfEcSpHO4IoT8r2EKxXsqX%2FNiA5fxsgqQMycviD3CIWSJVwpQ8sqLB7kVtS1F64bq7yiJpY541pwsBzifP5NpR6wrJ1u54kHb%2BKC2e3zym6tmyvlzCzM%3D&city=10863&tick=638881978745&locale=en-in&ckuid=0782016a-40d3-4e7a-86a4-8cab9dacec41&prid=0&gclid=Cj0KCQjw-NfDBhDyARIsAD-ILeBXva5TJhq-jGK3Si0BOfvtLo82iIstmv4-XMoqfU56Mshxz_UezUkaAhwMEALw_wcB&currency=INR&correlationId=55168ae7-8bc1-4224-a8eb-86ba246be729&analyticsSessionId=-1950121884218971931&pageTypeId=1&realLanguageId=15&languageId=1&origin=IN&stateCode=WB&cid=1922885&tag=6f147157-60b8-459f-af1a-9935d44970e9&userId=0782016a-40d3-4e7a-86a4-8cab9dacec41&whitelabelid=1&loginLvl=0&storefrontId=3&currencyId=27&currencyCode=INR&htmlLanguage=en-in&cultureInfoName=en-in&machineName=sg-pc-6h-acm-web-user-8697c4cd7c-gmgqx&trafficGroupId=5&trafficSubGroupId=122&aid=82361&useFullPageLogin=true&cttp=4&isRealUser=true&mode=production&browserFamily=Chrome&cdnDomain=agoda.net&checkIn=2025-08-12&checkOut=2025-08-13&rooms=1&adults=2&children=0&priceCur=INR&los=1&textToSearch=Darjeeling&travellerType=1&familyMode=off&ds=cgN73pCK5wrspJ7h&productType=-1"
    
    scraper = AgodaScraperOptimized(max_workers=5)
    
    # Run scraper (limit to 25 hotels for testing, remove max_hotels for full scraping)
    scraper.run_scraper(search_url, max_hotels=25)

if __name__ == "__main__":
    main()