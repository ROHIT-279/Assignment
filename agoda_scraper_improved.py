from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.common.exceptions import (
    NoSuchElementException, 
    TimeoutException, 
    ElementNotInteractableException,
    WebDriverException
)
import time
import pandas as pd
import logging
import traceback
import json

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AgodaScraper:
    def __init__(self):
        self.driver = None
        self.hotels_data = []
        self.seen_hotel_ids = set()
        
    def setup_driver(self):
        """Initialize Firefox driver with optimized options"""
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
        
        try:
            self.driver = webdriver.Firefox(options=options)
            logger.info("Firefox driver initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize driver: {str(e)}")
            return False
    
    def wait_for_page_load(self, timeout=30):
        """Wait for hotels to load on the page"""
        try:
            WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'li[data-selenium="hotel-item"]'))
            )
            logger.info("Hotels loaded successfully")
            return True
        except TimeoutException:
            logger.error("Timeout waiting for hotels to load")
            self.save_debug_page("timeout_page_source.html")
            return False
    
    def save_debug_page(self, filename):
        """Save current page source for debugging"""
        try:
            with open(filename, "w", encoding="utf-8") as f:
                f.write(self.driver.page_source)
            logger.info(f"Debug page saved to {filename}")
        except Exception as e:
            logger.error(f"Error saving debug page: {str(e)}")
    
    def extract_hotel_data(self, hotel_card):
        """Extract all data from a single hotel card"""
        hotel_data = {
            "hotel_id": "",
            "name": "",
            "price": "",
            "rating": "",
            "category": "",
            "location": "",
            "amenities": [],
            "review_count": ""
        }
        
        try:
            # Extract hotel ID
            hotel_data["hotel_id"] = hotel_card.get('data-hotelid', '')
            
            # Extract hotel name
            hotel_data["name"] = self.extract_hotel_name(hotel_card)
            
            # Extract price
            hotel_data["price"] = self.extract_hotel_price(hotel_card)
            
            # Extract rating
            hotel_data["rating"] = self.extract_hotel_rating(hotel_card)
            
            # Extract category (room type/category)
            hotel_data["category"] = self.extract_hotel_category(hotel_card)
            
            # Extract location
            hotel_data["location"] = self.extract_hotel_location(hotel_card)
            
            # Extract amenities
            hotel_data["amenities"] = self.extract_hotel_amenities(hotel_card)
            
            # Extract review count
            hotel_data["review_count"] = self.extract_review_count(hotel_card)
            
            logger.info(f"Extracted data for: {hotel_data['name'][:50]}...")
            
        except Exception as e:
            logger.error(f"Error extracting hotel data: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
        
        return hotel_data
    
    def extract_hotel_name(self, card):
        """Extract hotel name using multiple selectors"""
        name_selectors = [
            '[data-selenium="hotel-name"]',
            'h3 a',
            'h3',
            'h4',
            'h2',
            '.hotel-name',
            '.property-name',
            'a[href*="hotel"]',
            '[class*="name"]',
            '[class*="title"]'
        ]
        
        for selector in name_selectors:
            try:
                name_element = card.select_one(selector)
                if name_element:
                    name = name_element.get_text(strip=True)
                    if name and len(name) > 3:
                        return name
            except Exception as e:
                logger.debug(f"Error with name selector {selector}: {str(e)}")
                continue
        
        return ""
    
    def extract_hotel_price(self, card):
        """Extract hotel price using multiple selectors"""
        price_selectors = [
            '[data-selenium="hotel-price"]',
            '.price',
            '[class*="price"]',
            '[class*="rate"]',
            '[class*="cost"]',
            'span[class*="price"]',
            'div[class*="price"]'
        ]
        
        for selector in price_selectors:
            try:
                price_element = card.select_one(selector)
                if price_element:
                    price_text = price_element.get_text(strip=True)
                    if price_text and ('₹' in price_text or 'Rs' in price_text or 'INR' in price_text or 
                                     any(char.isdigit() for char in price_text)):
                        return price_text
            except Exception as e:
                logger.debug(f"Error with price selector {selector}: {str(e)}")
                continue
        
        return ""
    
    def extract_hotel_rating(self, card):
        """Extract hotel rating using multiple selectors"""
        rating_selectors = [
            '[data-selenium="review-score"]',
            '.rating',
            '.review-score',
            '.score',
            '[class*="rating"]',
            '[class*="score"]',
            '[class*="review"]'
        ]
        
        for selector in rating_selectors:
            try:
                rating_element = card.select_one(selector)
                if rating_element:
                    rating_text = rating_element.get_text(strip=True)
                    if rating_text and (rating_text.replace('.', '').replace(',', '').isdigit() or 
                                      'out of' in rating_text.lower()):
                        return rating_text
            except Exception as e:
                logger.debug(f"Error with rating selector {selector}: {str(e)}")
                continue
        
        return ""
    
    def extract_hotel_category(self, card):
        """Extract hotel category/room type using the provided selector"""
        category_selectors = [
            '[data-selenium="masterroom-title-name"]',
            '.Box-sc-kv6pi1-0.jJvGxG',
            '[class*="masterroom"]',
            '[class*="room-type"]',
            '[class*="category"]',
            '[data-selenium*="room"]',
            '[data-selenium*="category"]'
        ]
        
        for selector in category_selectors:
            try:
                category_element = card.select_one(selector)
                if category_element:
                    category_text = category_element.get_text(strip=True)
                    if category_text and len(category_text) > 2:
                        return category_text
            except Exception as e:
                logger.debug(f"Error with category selector {selector}: {str(e)}")
                continue
        
        return ""
    
    def extract_hotel_location(self, card):
        """Extract hotel location"""
        location_selectors = [
            '[data-selenium="hotel-location"]',
            '.location',
            '.address',
            '[class*="location"]',
            '[class*="address"]',
            '[class*="area"]'
        ]
        
        for selector in location_selectors:
            try:
                location_element = card.select_one(selector)
                if location_element:
                    location_text = location_element.get_text(strip=True)
                    if location_text and len(location_text) > 2:
                        return location_text
            except Exception as e:
                logger.debug(f"Error with location selector {selector}: {str(e)}")
                continue
        
        return ""
    
    def extract_hotel_amenities(self, card):
        """Extract hotel amenities"""
        amenities = []
        amenity_selectors = [
            '[data-selenium*="amenity"]',
            '.amenity',
            '.facility',
            '[class*="amenity"]',
            '[class*="facility"]',
            '[class*="feature"]'
        ]
        
        for selector in amenity_selectors:
            try:
                amenity_elements = card.select(selector)
                for element in amenity_elements:
                    amenity_text = element.get_text(strip=True)
                    if amenity_text and len(amenity_text) > 2:
                        amenities.append(amenity_text)
            except Exception as e:
                logger.debug(f"Error with amenity selector {selector}: {str(e)}")
                continue
        
        return amenities
    
    def extract_review_count(self, card):
        """Extract review count"""
        review_selectors = [
            '[data-selenium="review-count"]',
            '.review-count',
            '[class*="review"]',
            '[class*="count"]'
        ]
        
        for selector in review_selectors:
            try:
                review_element = card.select_one(selector)
                if review_element:
                    review_text = review_element.get_text(strip=True)
                    if review_text and any(char.isdigit() for char in review_text):
                        return review_text
            except Exception as e:
                logger.debug(f"Error with review selector {selector}: {str(e)}")
                continue
        
        return ""
    
    def scroll_and_load_more(self):
        """Scroll page and attempt to load more hotels"""
        try:
            # Scroll to bottom
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(3)
            
            # Try to click load more or pagination buttons
            next_selectors = [
                'button[data-selenium="pagination-next-btn"]',
                'button[aria-label="Next page"]',
                '.pagination-next',
                '.load-more-btn',
                'button[class*="next"]',
                'a[aria-label="Next page"]',
                'button[class*="load-more"]'
            ]
            
            for selector in next_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        button = elements[0]
                        if button.is_enabled() and button.is_displayed():
                            logger.info(f"Clicking load more button: {selector}")
                            button.click()
                            time.sleep(5)
                            return True
                except Exception as e:
                    logger.debug(f"Error with selector {selector}: {str(e)}")
                    continue
            
            return False
            
        except Exception as e:
            logger.error(f"Error in scroll_and_load_more: {str(e)}")
            return False
    
    def scrape_hotels(self, url, max_iterations=3):
        """Main scraping function"""
        if not self.setup_driver():
            return False
        
        try:
            logger.info("Loading page...")
            self.driver.get(url)
            
            if not self.wait_for_page_load():
                return False
            
            # Give extra time for dynamic content
            time.sleep(10)
            
            for iteration in range(max_iterations):
                logger.info(f"Scraping iteration {iteration + 1}/{max_iterations}")
                
                # Get current page source
                soup = BeautifulSoup(self.driver.page_source, "html.parser")
                hotel_items = soup.select('li[data-selenium="hotel-item"]')
                
                logger.info(f"Found {len(hotel_items)} hotel items on page")
                
                if len(hotel_items) == 0:
                    logger.warning("No hotel items found!")
                    self.save_debug_page(f"debug_no_hotels_iter_{iteration}.html")
                    break
                
                # Process each hotel
                for hotel_card in hotel_items:
                    hotel_id = hotel_card.get('data-hotelid', '')
                    
                    if hotel_id not in self.seen_hotel_ids:
                        self.seen_hotel_ids.add(hotel_id)
                        hotel_data = self.extract_hotel_data(hotel_card)
                        
                        if hotel_data["name"]:  # Only add if name found
                            self.hotels_data.append(hotel_data)
                
                # Try to load more hotels
                if not self.scroll_and_load_more():
                    logger.info("No more hotels to load")
                    break
            
            logger.info(f"Scraping completed. Total hotels collected: {len(self.hotels_data)}")
            return True
            
        except Exception as e:
            logger.error(f"Error during scraping: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return False
    
    def save_data(self):
        """Save scraped data to files"""
        if not self.hotels_data:
            logger.warning("No data to save!")
            return
        
        # Save to CSV
        df = pd.DataFrame(self.hotels_data)
        df.to_csv("agoda_hotels_improved.csv", index=False, encoding="utf-8")
        logger.info(f"Saved {len(self.hotels_data)} hotels to agoda_hotels_improved.csv")
        
        # Save to JSON for better structure
        with open("agoda_hotels_improved.json", "w", encoding="utf-8") as f:
            json.dump(self.hotels_data, f, ensure_ascii=False, indent=2)
        logger.info("Saved data to agoda_hotels_improved.json")
        
        # Print summary
        self.print_summary()
    
    def print_summary(self):
        """Print scraping summary"""
        if not self.hotels_data:
            return
        
        df = pd.DataFrame(self.hotels_data)
        
        print("\n" + "="*50)
        print("AGODA SCRAPING SUMMARY")
        print("="*50)
        print(f"Total hotels scraped: {len(self.hotels_data)}")
        print(f"Hotels with names: {len([h for h in self.hotels_data if h['name']])}")
        print(f"Hotels with prices: {len([h for h in self.hotels_data if h['price']])}")
        print(f"Hotels with ratings: {len([h for h in self.hotels_data if h['rating']])}")
        print(f"Hotels with categories: {len([h for h in self.hotels_data if h['category']])}")
        print(f"Hotels with locations: {len([h for h in self.hotels_data if h['location']])}")
        print(f"Hotels with amenities: {len([h for h in self.hotels_data if h['amenities']])}")
        
        print("\nSample of first 5 hotels:")
        print("-" * 50)
        for i, hotel in enumerate(self.hotels_data[:5]):
            print(f"{i+1}. {hotel['name'][:50]}...")
            print(f"   Price: {hotel['price']}")
            print(f"   Rating: {hotel['rating']}")
            print(f"   Category: {hotel['category']}")
            print(f"   Location: {hotel['location']}")
            if hotel['amenities']:
                print(f"   Amenities: {', '.join(hotel['amenities'][:3])}")
            print()
    
    def cleanup(self):
        """Clean up resources"""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("Driver closed successfully")
            except Exception as e:
                logger.error(f"Error closing driver: {str(e)}")

def main():
    """Main execution function"""
    url = "https://www.agoda.com/en-in/search?guid=ac34b805-fbbb-4a54-91f6-72bd44251297&asq=oSBZUdCJkTqIcAJrG1AX8Jufa9Vwpz6XltTHq4n%2B9gNpSLc%2BT%2BpB%2F8FnmmA8sOyAJ0WZY5hpLWEr%2Fk8qr78gW4DMS7e7llLtqq76yKsoLJ2OoQ3gw8ln%2FUAwfEcSpHO4IoT8r2EKxXsqX%2FNiA5fxsgqQMycviD3CIWSJVwpQ8sqLB7kVtS1F64bq7yiJpY541pwsBzifP5NpR6wrJ1u54kHb%2BKC2e3zym6tmyvlzCzM%3D&city=10863&tick=638881978745&locale=en-in&ckuid=0782016a-40d3-4e7a-86a4-8cab9dacec41&prid=0&gclid=Cj0KCQjw-NfDBhDyARIsAD-ILeBXva5TJhq-jGK3Si0BOfvtLo82iIstmv4-XMoqfU56Mshxz_UezUkaAhwMEALw_wcB&currency=INR&correlationId=55168ae7-8bc1-4224-a8eb-86ba246be729&analyticsSessionId=-1950121884218971931&pageTypeId=1&realLanguageId=15&languageId=1&origin=IN&stateCode=WB&cid=1922885&tag=6f147157-60b8-459f-af1a-9935d44970e9&userId=0782016a-40d3-4e7a-86a4-8cab9dacec41&whitelabelid=1&loginLvl=0&storefrontId=3&currencyId=27&currencyCode=INR&htmlLanguage=en-in&cultureInfoName=en-in&machineName=sg-pc-6h-acm-web-user-8697c4cd7c-gmgqx&trafficGroupId=5&trafficSubGroupId=122&aid=82361&useFullPageLogin=true&cttp=4&isRealUser=true&mode=production&browserFamily=Chrome&cdnDomain=agoda.net&checkIn=2025-08-12&checkOut=2025-08-13&rooms=1&adults=2&children=0&priceCur=INR&los=1&textToSearch=Darjeeling&travellerType=1&familyMode=off&ds=cgN73pCK5wrspJ7h&productType=-1"
    
    scraper = AgodaScraper()
    
    try:
        success = scraper.scrape_hotels(url, max_iterations=3)
        if success:
            scraper.save_data()
        else:
            logger.error("Scraping failed!")
    except KeyboardInterrupt:
        logger.info("Scraping interrupted by user")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
    finally:
        scraper.cleanup()

if __name__ == "__main__":
    main()