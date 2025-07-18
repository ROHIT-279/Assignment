from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
import time
import threading
import csv
import json
from datetime import datetime
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
import queue

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AgodaScraper:
    def __init__(self, max_workers=5):
        self.max_workers = max_workers
        self.hotel_queue = queue.Queue()
        self.results_queue = queue.Queue()
        self.hotel_data = []
        
    def setup_driver(self, headless=True):
        """Setup Firefox driver with options"""
        options = Options()
        if headless:
            options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        
        driver = webdriver.Firefox(options=options)
        driver.implicitly_wait(10)
        return driver

    def scrape_initial_hotels(self, url):
        """Scrape initial hotel list and extract hotel URLs"""
        driver = self.setup_driver(headless=False)
        hotel_urls = []
        
        try:
            driver.get(url)
            WebDriverWait(driver, 15).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'li[data-selenium="hotel-item"]'))
            )
            
            iterations = 8
            scroll_count = 0
            
            while iterations > 0:
                try:
                    # Scroll to load more hotels
                    driver.execute_script("window.scrollTo(0, document.body.scrollHeight * 0.75);")
                    time.sleep(3)
                    scroll_count += 1
                    
                    # Get hotel URLs
                    soup = BeautifulSoup(driver.page_source, "html.parser")
                    hotel_elements = soup.select('li[data-selenium="hotel-item"]')
                    
                    for hotel in hotel_elements:
                        hotel_link = hotel.find('a', {'data-testid': 'property-name-link'})
                        if hotel_link and hotel_link.get('href'):
                            full_url = "https://www.agoda.com" + hotel_link.get('href')
                            if full_url not in hotel_urls:
                                hotel_urls.append(full_url)
                                logger.info(f"Found hotel URL: {full_url}")
                    
                    # Try to click next page
                    try:
                        next_button = driver.find_element(By.CSS_SELECTOR, 'button[data-selenium="pagination-next-btn"]')
                        if next_button.is_enabled():
                            next_button.click()
                            time.sleep(5)
                        else:
                            break
                    except:
                        break
                        
                    iterations -= 1
                    
                except Exception as e:
                    logger.error(f"Error in iteration: {e}")
                    break
            
            logger.info(f"Total hotels found: {len(hotel_urls)}, Total scrolls: {scroll_count}")
            
        except Exception as e:
            logger.error(f"Error scraping initial hotels: {e}")
        finally:
            driver.quit()
            
        return hotel_urls

    def extract_hotel_details(self, hotel_url, worker_id):
        """Extract detailed information from a single hotel page"""
        driver = self.setup_driver(headless=True)
        hotel_data = {
            'hotel_url': hotel_url,
            'hotel_name': '',
            'room_categories': [],
            'reviews': [],
            'overall_rating': '',
            'worker_id': worker_id
        }
        
        try:
            driver.get(hotel_url)
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            time.sleep(3)
            
            soup = BeautifulSoup(driver.page_source, "html.parser")
            
            # Extract hotel name
            hotel_name_elem = soup.find('h1')
            if hotel_name_elem:
                hotel_data['hotel_name'] = hotel_name_elem.get_text(strip=True)
            
            # Extract overall rating
            rating_elem = soup.find('div', class_=lambda x: x and 'rating' in x.lower())
            if rating_elem:
                hotel_data['overall_rating'] = rating_elem.get_text(strip=True)
            
            # Extract room categories and prices
            room_elements = soup.find_all('div', class_=lambda x: x and 'cor-tooltip-wrapper' in x)
            for room_elem in room_elements:
                room_info = {
                    'category': '',
                    'price': ''
                }
                
                # Extract room category
                category_elem = room_elem.find('div', {'data-info-type': 'room-type'})
                if category_elem:
                    room_info['category'] = category_elem.get_text(strip=True)
                
                # Extract price
                price_elem = room_elem.find('span', class_=lambda x: x and 'price' in x.lower())
                if price_elem:
                    room_info['price'] = price_elem.get_text(strip=True)
                
                if room_info['category'] or room_info['price']:
                    hotel_data['room_categories'].append(room_info)
            
            # Navigate to reviews section if available
            try:
                reviews_section = driver.find_element(By.CSS_SELECTOR, 'a[href*="reviews"]')
                reviews_section.click()
                time.sleep(3)
                
                # Extract reviews
                soup = BeautifulSoup(driver.page_source, "html.parser")
                self.extract_reviews(soup, hotel_data)
                
            except Exception as e:
                logger.warning(f"Could not access reviews for {hotel_url}: {e}")
            
            logger.info(f"Worker {worker_id}: Completed {hotel_data['hotel_name']}")
            
        except Exception as e:
            logger.error(f"Worker {worker_id}: Error extracting details from {hotel_url}: {e}")
        finally:
            driver.quit()
            
        return hotel_data

    def extract_reviews(self, soup, hotel_data):
        """Extract reviews from the reviews page"""
        review_bubbles = soup.find_all('div', class_=lambda x: x and 'Review-comment-bubble' in x)
        
        for bubble in review_bubbles[:10]:  # Limit to first 10 reviews
            review_data = {
                'reviewer_info': '',
                'rating': '',
                'date': '',
                'comment': ''
            }
            
            # Extract reviewer info and room type
            reviewer_elem = bubble.find('div', class_=lambda x: x and 'Review-comment-reviewer' in x)
            if reviewer_elem:
                review_data['reviewer_info'] = reviewer_elem.get_text(strip=True)
            
            # Extract rating
            rating_elem = bubble.find('div', class_=lambda x: x and 'Review-comment-leftScore' in x)
            if rating_elem:
                review_data['rating'] = rating_elem.get_text(strip=True)
            
            # Extract date
            date_elem = bubble.find('div', class_=lambda x: x and 'Typography' in x)
            if date_elem:
                review_data['date'] = date_elem.get_text(strip=True)
            
            # Extract comment
            comment_elem = bubble.find('div', class_=lambda x: x and 'Review-comment-left' in x)
            if comment_elem:
                review_data['comment'] = comment_elem.get_text(strip=True)
            
            hotel_data['reviews'].append(review_data)

    def process_hotels_batch(self, hotel_urls_batch):
        """Process a batch of hotels using ThreadPoolExecutor"""
        batch_results = []
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit tasks
            future_to_url = {
                executor.submit(self.extract_hotel_details, url, i): url 
                for i, url in enumerate(hotel_urls_batch)
            }
            
            # Collect results
            for future in as_completed(future_to_url):
                url = future_to_url[future]
                try:
                    result = future.result()
                    batch_results.append(result)
                    logger.info(f"Completed processing: {result['hotel_name']}")
                except Exception as e:
                    logger.error(f"Error processing {url}: {e}")
        
        return batch_results

    def save_to_csv(self, filename="agoda_hotels_detailed.csv"):
        """Save extracted data to CSV file"""
        if not self.hotel_data:
            logger.warning("No data to save")
            return
        
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = [
                'hotel_name', 'hotel_url', 'overall_rating', 
                'room_category', 'room_price', 'reviewer_info', 
                'review_rating', 'review_date', 'review_comment'
            ]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for hotel in self.hotel_data:
                # Write room categories
                if hotel['room_categories']:
                    for room in hotel['room_categories']:
                        # Write reviews for each room category
                        if hotel['reviews']:
                            for review in hotel['reviews']:
                                writer.writerow({
                                    'hotel_name': hotel['hotel_name'],
                                    'hotel_url': hotel['hotel_url'],
                                    'overall_rating': hotel['overall_rating'],
                                    'room_category': room['category'],
                                    'room_price': room['price'],
                                    'reviewer_info': review['reviewer_info'],
                                    'review_rating': review['rating'],
                                    'review_date': review['date'],
                                    'review_comment': review['comment']
                                })
                        else:
                            # Write room info without reviews
                            writer.writerow({
                                'hotel_name': hotel['hotel_name'],
                                'hotel_url': hotel['hotel_url'],
                                'overall_rating': hotel['overall_rating'],
                                'room_category': room['category'],
                                'room_price': room['price'],
                                'reviewer_info': '',
                                'review_rating': '',
                                'review_date': '',
                                'review_comment': ''
                            })
                else:
                    # Write hotel info without room categories
                    if hotel['reviews']:
                        for review in hotel['reviews']:
                            writer.writerow({
                                'hotel_name': hotel['hotel_name'],
                                'hotel_url': hotel['hotel_url'],
                                'overall_rating': hotel['overall_rating'],
                                'room_category': '',
                                'room_price': '',
                                'reviewer_info': review['reviewer_info'],
                                'review_rating': review['rating'],
                                'review_date': review['date'],
                                'review_comment': review['comment']
                            })
                    else:
                        writer.writerow({
                            'hotel_name': hotel['hotel_name'],
                            'hotel_url': hotel['hotel_url'],
                            'overall_rating': hotel['overall_rating'],
                            'room_category': '',
                            'room_price': '',
                            'reviewer_info': '',
                            'review_rating': '',
                            'review_date': '',
                            'review_comment': ''
                        })
        
        logger.info(f"Data saved to {filename}")

    def run_scraper(self, initial_url):
        """Main method to run the complete scraping process"""
        logger.info("Starting Agoda scraper...")
        
        # Step 1: Get hotel URLs
        logger.info("Extracting hotel URLs...")
        hotel_urls = self.scrape_initial_hotels(initial_url)
        
        if not hotel_urls:
            logger.error("No hotel URLs found")
            return
        
        logger.info(f"Found {len(hotel_urls)} hotels to process")
        
        # Step 2: Process hotels in batches of 5
        batch_size = 5
        total_batches = (len(hotel_urls) + batch_size - 1) // batch_size
        
        for i in range(0, len(hotel_urls), batch_size):
            batch_num = (i // batch_size) + 1
            batch_urls = hotel_urls[i:i + batch_size]
            
            logger.info(f"Processing batch {batch_num}/{total_batches} with {len(batch_urls)} hotels")
            
            # Process current batch
            batch_results = self.process_hotels_batch(batch_urls)
            self.hotel_data.extend(batch_results)
            
            logger.info(f"Completed batch {batch_num}/{total_batches}")
            
            # Save intermediate results
            if batch_results:
                self.save_to_csv(f"agoda_batch_{batch_num}.csv")
        
        # Step 3: Save final results
        logger.info("Saving final results...")
        self.save_to_csv("agoda_hotels_final.csv")
        
        # Save raw data as JSON for backup
        with open("agoda_raw_data.json", "w", encoding="utf-8") as f:
            json.dump(self.hotel_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Scraping completed! Total hotels processed: {len(self.hotel_data)}")

def main():
    # Your original URL
    url = "https://www.agoda.com/en-in/search?guid=ac34b805-fbbb-4a54-91f6-72bd44251297&asq=oSBZUdCJkTqIcAJrG1AX8Jufa9Vwpz6XltTHq4n%2B9gNpSLc%2BT%2BpB%2F8FnmmA8sOyAJ0WZY5hpLWEr%2Fk8qr78gW4DMS7e7llLtqq76yKsoLJ2OoQ3gw8ln%2FUAwfEcSpHO4IoT8r2EKxXsqX%2FNiA5fxsgqQMycviD3CIWSJVwpQ8sqLB7kVtS1F64bq7yiJpY541pwsBzifP5NpR6wrJ1u54kHb%2BKC2e3zym6tmyvlzCzM%3D&city=10863&tick=638881978745&locale=en-in&ckuid=0782016a-40d3-4e7a-86a4-8cab9dacec41&prid=0&gclid=Cj0KCQjw-NfDBhDyARIsAD-ILeBXva5TJhq-jGK3Si0BOfvtLo82iIstmv4-XMoqfU56Mshxz_UezUkaAhwMEALw_wcB&currency=INR&correlationId=55168ae7-8bc1-4224-a8eb-86ba246be729&analyticsSessionId=-1950121884218971931&pageTypeId=1&realLanguageId=15&languageId=1&origin=IN&stateCode=WB&cid=1922885&tag=6f147157-60b8-459f-af1a-9935d44970e9&userId=0782016a-40d3-4e7a-86a4-8cab9dacec41&whitelabelid=1&loginLvl=0&storefrontId=3&currencyId=27&currencyCode=INR&htmlLanguage=en-in&cultureInfoName=en-in&machineName=sg-pc-6h-acm-web-user-8697c4cd7c-gmgqx&trafficGroupId=5&trafficSubGroupId=122&aid=82361&useFullPageLogin=true&cttp=4&isRealUser=true&mode=production&browserFamily=Chrome&cdnDomain=agoda.net&checkIn=2025-08-12&checkOut=2025-08-13&rooms=1&adults=2&children=0&priceCur=INR&los=1&textToSearch=Darjeeling&travellerType=1&familyMode=off&ds=cgN73pCK5wrspJ7h&productType=-1"
    
    scraper = AgodaScraper(max_workers=5)
    scraper.run_scraper(url)

if __name__ == "__main__":
    main()