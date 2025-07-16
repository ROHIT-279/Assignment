from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
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
import re

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AgodaScraperRobust:
    def __init__(self):
        self.driver = None
        self.hotels_data = []
        self.seen_hotel_ids = set()
        self.debug_info = {
            "page_loads": 0,
            "errors": [],
            "selectors_tried": [],
            "hotels_found_per_iteration": []
        }
        
    def setup_driver(self):
        """Initialize Firefox driver with enhanced options for Agoda"""
        options = Options()
        
        # Enhanced options for better compatibility
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-plugins")
        options.add_argument("--disable-images")  # Faster loading
        options.add_argument("--window-size=1920,1080")
        
        # More realistic user agent
        options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
        # Additional preferences
        options.set_preference("dom.webdriver.enabled", False)
        options.set_preference("useAutomationExtension", False)
        options.set_preference("general.useragent.override", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
        try:
            self.driver = webdriver.Firefox(options=options)
            
            # Execute scripts to hide automation
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            logger.info("Firefox driver initialized successfully with enhanced settings")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize driver: {str(e)}")
            return False
    
    def wait_for_page_load_robust(self, url, timeout=60):
        """Enhanced page loading with multiple detection strategies"""
        logger.info(f"Loading page: {url}")
        
        try:
            self.driver.get(url)
            self.debug_info["page_loads"] += 1
            
            # Wait for basic page structure first
            logger.info("Waiting for basic page structure...")
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Save initial page for debugging
            self.save_debug_page("initial_page_load.html")
            
            # Check if we're blocked or redirected
            current_url = self.driver.current_url
            page_title = self.driver.title.lower()
            
            logger.info(f"Current URL: {current_url}")
            logger.info(f"Page title: {self.driver.title}")
            
            # Check for common blocking patterns
            if any(blocked in page_title for blocked in ['blocked', 'access denied', 'forbidden', 'error']):
                logger.error(f"Possible blocking detected. Page title: {self.driver.title}")
                return False
            
            # Multiple hotel detection strategies
            hotel_selectors = [
                'li[data-selenium="hotel-item"]',           # Original selector
                '[data-selenium="hotel-item"]',             # More general
                '.hotel-item',                              # Class-based
                '[data-testid="property-card"]',            # Alternative data attribute
                '.property-card',                           # Common class name
                '[class*="hotel"]',                         # Any class containing "hotel"
                '[class*="property"]',                      # Any class containing "property"
                'article[data-selenium]',                   # Article elements with data-selenium
                'div[data-hotelid]',                        # Direct hotel ID attribute
                '.search-result',                           # Generic search result
            ]
            
            logger.info("Trying multiple hotel detection strategies...")
            
            for i, selector in enumerate(hotel_selectors):
                try:
                    logger.info(f"Strategy {i+1}: Trying selector '{selector}'")
                    self.debug_info["selectors_tried"].append(selector)
                    
                    # Wait for hotels with this selector
                    WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    
                    # Check how many elements we found
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    logger.info(f"✅ Success! Found {len(elements)} elements with selector '{selector}'")
                    
                    if len(elements) > 0:
                        # Additional wait for content to stabilize
                        time.sleep(5)
                        return True
                        
                except TimeoutException:
                    logger.info(f"❌ No elements found with selector '{selector}'")
                    continue
                except Exception as e:
                    logger.warning(f"Error with selector '{selector}': {str(e)}")
                    continue
            
            # If all specific selectors fail, try to detect any content
            logger.info("All hotel selectors failed. Checking for any dynamic content...")
            
            # Check page length and content
            page_source = self.driver.page_source
            logger.info(f"Page source length: {len(page_source)} characters")
            
            # Look for hotel-related keywords in the page
            hotel_keywords = ['hotel', 'property', 'accommodation', 'booking', 'room', 'suite']
            found_keywords = [kw for kw in hotel_keywords if kw in page_source.lower()]
            logger.info(f"Found hotel keywords: {found_keywords}")
            
            if len(found_keywords) >= 2:
                logger.info("Page seems to have hotel-related content. Proceeding with extraction...")
                self.save_debug_page("keyword_based_detection.html")
                return True
            
            logger.error("No hotel content detected with any strategy")
            return False
            
        except Exception as e:
            logger.error(f"Error during page loading: {str(e)}")
            self.debug_info["errors"].append(f"Page load error: {str(e)}")
            return False
    
    def detect_hotels_flexible(self):
        """Flexible hotel detection using multiple strategies"""
        soup = BeautifulSoup(self.driver.page_source, "html.parser")
        
        # Strategy 1: Original selectors
        hotel_selectors = [
            'li[data-selenium="hotel-item"]',
            '[data-selenium="hotel-item"]',
            'div[data-hotelid]',
            '.hotel-item',
            '[data-testid="property-card"]',
            '.property-card',
            'article[data-selenium]'
        ]
        
        hotels_found = []
        
        for selector in hotel_selectors:
            try:
                elements = soup.select(selector)
                if elements:
                    logger.info(f"Found {len(elements)} hotels with selector: {selector}")
                    hotels_found.extend(elements)
                    break  # Use first successful selector
            except Exception as e:
                logger.debug(f"Error with selector {selector}: {str(e)}")
                continue
        
        # Strategy 2: If no hotels found, try pattern matching
        if not hotels_found:
            logger.info("No hotels found with standard selectors. Trying pattern matching...")
            
            # Look for elements that might contain hotel data
            potential_hotels = []
            
            # Look for elements with hotel-like attributes
            for element in soup.find_all(['div', 'article', 'li', 'section']):
                # Check for hotel-related attributes
                attrs = element.attrs
                attr_text = ' '.join([str(v) for v in attrs.values() if isinstance(v, str)])
                
                if any(keyword in attr_text.lower() for keyword in ['hotel', 'property', 'accommodation']):
                    potential_hotels.append(element)
            
            if potential_hotels:
                logger.info(f"Found {len(potential_hotels)} potential hotels using pattern matching")
                hotels_found = potential_hotels[:50]  # Limit to avoid too many false positives
        
        # Strategy 3: Text-based detection
        if not hotels_found:
            logger.info("Trying text-based hotel detection...")
            
            # Look for elements containing hotel names or prices
            price_patterns = [r'₹\s*[\d,]+', r'Rs\s*[\d,]+', r'INR\s*[\d,]+']
            
            for element in soup.find_all(['div', 'span', 'p']):
                text = element.get_text().strip()
                if text and any(re.search(pattern, text) for pattern in price_patterns):
                    parent = element.find_parent(['div', 'article', 'li'])
                    if parent and parent not in hotels_found:
                        hotels_found.append(parent)
        
        logger.info(f"Total hotels detected: {len(hotels_found)}")
        self.debug_info["hotels_found_per_iteration"].append(len(hotels_found))
        
        return hotels_found
    
    def extract_hotel_data_flexible(self, hotel_element):
        """Enhanced hotel data extraction with more flexible selectors"""
        hotel_data = {
            "hotel_id": "",
            "name": "",
            "price": "",
            "rating": "",
            "category": "",
            "location": "",
            "amenities": [],
            "review_count": "",
            "extraction_method": ""
        }
        
        try:
            # Extract hotel ID
            hotel_data["hotel_id"] = (
                hotel_element.get('data-hotelid') or 
                hotel_element.get('data-testid') or 
                hotel_element.get('id') or 
                str(hash(str(hotel_element)[:200]))
            )
            
            # Enhanced name extraction
            hotel_data["name"] = self.extract_text_flexible(hotel_element, [
                '[data-selenium="hotel-name"]',
                'h1', 'h2', 'h3', 'h4',
                'a[href*="hotel"]',
                '.hotel-name', '.property-name',
                '[class*="name"]', '[class*="title"]',
                'strong', 'b'
            ])
            
            # Enhanced price extraction
            hotel_data["price"] = self.extract_text_flexible(hotel_element, [
                '[data-selenium="hotel-price"]',
                '.price', '[class*="price"]',
                '[class*="rate"]', '[class*="cost"]'
            ], patterns=[r'₹\s*[\d,]+', r'Rs\s*[\d,]+', r'INR\s*[\d,]+'])
            
            # Enhanced rating extraction
            hotel_data["rating"] = self.extract_text_flexible(hotel_element, [
                '[data-selenium="review-score"]',
                '.rating', '.score', '.review-score',
                '[class*="rating"]', '[class*="score"]'
            ])
            
            # Enhanced category extraction (your main requirement)
            hotel_data["category"] = self.extract_text_flexible(hotel_element, [
                '[data-selenium="masterroom-title-name"]',  # Your primary selector
                '.Box-sc-kv6pi1-0.jJvGxG',                 # Your specific class
                '[class*="masterroom"]',
                '[class*="room-type"]', '[class*="category"]',
                '[data-selenium*="room"]', '[data-selenium*="category"]',
                '.room-name', '.room-type'
            ])
            
            # Enhanced location extraction
            hotel_data["location"] = self.extract_text_flexible(hotel_element, [
                '[data-selenium="hotel-location"]',
                '.location', '.address', '.area',
                '[class*="location"]', '[class*="address"]'
            ])
            
            # Extract amenities
            amenities = []
            amenity_elements = hotel_element.find_all(['span', 'div'], string=re.compile(r'(wifi|pool|spa|gym|parking)', re.I))
            for elem in amenity_elements:
                amenity_text = elem.get_text().strip()
                if amenity_text and len(amenity_text) < 50:
                    amenities.append(amenity_text)
            hotel_data["amenities"] = amenities[:5]  # Limit to 5 amenities
            
            # Review count
            hotel_data["review_count"] = self.extract_text_flexible(hotel_element, [
                '[data-selenium="review-count"]',
                '.review-count', '[class*="review"]'
            ], patterns=[r'\d+\s*(review|rating)'])
            
            # Mark extraction method
            hotel_data["extraction_method"] = "flexible"
            
            if hotel_data["name"]:
                logger.info(f"Extracted: {hotel_data['name'][:30]}... | Category: {hotel_data['category'][:20]}... | Price: {hotel_data['price'][:15]}...")
            
        except Exception as e:
            logger.error(f"Error extracting hotel data: {str(e)}")
            self.debug_info["errors"].append(f"Extraction error: {str(e)}")
        
        return hotel_data
    
    def extract_text_flexible(self, element, selectors, patterns=None):
        """Flexible text extraction with multiple selectors and optional regex patterns"""
        for selector in selectors:
            try:
                found_element = element.select_one(selector)
                if found_element:
                    text = found_element.get_text(strip=True)
                    if text:
                        # If patterns provided, check if text matches
                        if patterns:
                            for pattern in patterns:
                                match = re.search(pattern, text)
                                if match:
                                    return match.group()
                        else:
                            return text
            except Exception:
                continue
        
        # If no selector worked and patterns provided, search in all text
        if patterns:
            all_text = element.get_text()
            for pattern in patterns:
                match = re.search(pattern, all_text)
                if match:
                    return match.group()
        
        return ""
    
    def save_debug_page(self, filename):
        """Enhanced debug page saving with metadata"""
        try:
            with open(filename, "w", encoding="utf-8") as f:
                f.write(f"<!-- Debug info: {json.dumps(self.debug_info, indent=2)} -->\n")
                f.write(self.driver.page_source)
            logger.info(f"Debug page saved to {filename}")
        except Exception as e:
            logger.error(f"Error saving debug page: {str(e)}")
    
    def scrape_hotels_robust(self, url, max_iterations=3):
        """Enhanced scraping with robust error handling"""
        if not self.setup_driver():
            return False
        
        try:
            # Enhanced page loading
            if not self.wait_for_page_load_robust(url):
                logger.error("Failed to load page or detect hotels")
                self.save_debug_page("failed_page_load.html")
                return False
            
            # Wait for page to stabilize
            logger.info("Waiting for page to stabilize...")
            time.sleep(10)
            
            for iteration in range(max_iterations):
                logger.info(f"Scraping iteration {iteration + 1}/{max_iterations}")
                
                # Flexible hotel detection
                hotel_elements = self.detect_hotels_flexible()
                
                if not hotel_elements:
                    logger.warning(f"No hotels found in iteration {iteration + 1}")
                    self.save_debug_page(f"no_hotels_iter_{iteration}.html")
                    
                    if iteration == 0:  # First iteration failed
                        logger.info("First iteration failed. Trying page interaction...")
                        # Try scrolling to trigger content loading
                        self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                        time.sleep(5)
                        self.driver.execute_script("window.scrollTo(0, 0);")
                        time.sleep(5)
                        continue
                    else:
                        break
                
                # Process hotels
                new_hotels_count = 0
                for hotel_element in hotel_elements:
                    hotel_data = self.extract_hotel_data_flexible(hotel_element)
                    hotel_id = hotel_data["hotel_id"]
                    
                    if hotel_id not in self.seen_hotel_ids and hotel_data["name"]:
                        self.seen_hotel_ids.add(hotel_id)
                        self.hotels_data.append(hotel_data)
                        new_hotels_count += 1
                
                logger.info(f"Iteration {iteration + 1}: Found {new_hotels_count} new hotels")
                
                # Try to load more content
                if not self.scroll_and_load_more():
                    logger.info("No more content to load")
                    break
            
            logger.info(f"Scraping completed. Total hotels: {len(self.hotels_data)}")
            
            # Final debug information
            if self.hotels_data:
                self.save_debug_page("successful_scraping.html")
                return True
            else:
                logger.error("No hotels were successfully extracted")
                self.save_debug_page("zero_extraction.html")
                return False
                
        except Exception as e:
            logger.error(f"Error during scraping: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            self.debug_info["errors"].append(f"Scraping error: {str(e)}")
            return False
    
    def scroll_and_load_more(self):
        """Enhanced scrolling and loading mechanism"""
        try:
            # Scroll down slowly to trigger lazy loading
            for i in range(3):
                self.driver.execute_script(f"window.scrollTo(0, document.body.scrollHeight * {(i+1)/3});")
                time.sleep(2)
            
            # Try various load more mechanisms
            load_more_selectors = [
                'button[data-selenium="pagination-next-btn"]',
                'button[aria-label="Next page"]',
                '.pagination-next',
                '.load-more-btn',
                'button[class*="next"]',
                'button[class*="load-more"]',
                'a[class*="next"]'
            ]
            
            for selector in load_more_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        button = elements[0]
                        if button.is_enabled() and button.is_displayed():
                            logger.info(f"Clicking load more: {selector}")
                            self.driver.execute_script("arguments[0].click();", button)
                            time.sleep(5)
                            return True
                except Exception as e:
                    continue
            
            return False
            
        except Exception as e:
            logger.error(f"Error in scroll_and_load_more: {str(e)}")
            return False
    
    def save_data_enhanced(self):
        """Enhanced data saving with debug information"""
        if not self.hotels_data:
            logger.warning("No data to save!")
            return
        
        # Save main data
        df = pd.DataFrame(self.hotels_data)
        df.to_csv("agoda_hotels_robust.csv", index=False, encoding="utf-8")
        
        with open("agoda_hotels_robust.json", "w", encoding="utf-8") as f:
            json.dump(self.hotels_data, f, ensure_ascii=False, indent=2)
        
        # Save debug information
        with open("scraping_debug_info.json", "w", encoding="utf-8") as f:
            json.dump(self.debug_info, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Saved {len(self.hotels_data)} hotels and debug info")
        
        # Enhanced summary
        self.print_enhanced_summary()
    
    def print_enhanced_summary(self):
        """Print detailed scraping summary"""
        if not self.hotels_data:
            return
        
        print("\n" + "="*60)
        print("🏨 AGODA ROBUST SCRAPING SUMMARY")
        print("="*60)
        
        # Statistics
        total = len(self.hotels_data)
        with_names = len([h for h in self.hotels_data if h['name']])
        with_prices = len([h for h in self.hotels_data if h['price']])
        with_ratings = len([h for h in self.hotels_data if h['rating']])
        with_categories = len([h for h in self.hotels_data if h['category']])
        with_locations = len([h for h in self.hotels_data if h['location']])
        
        print(f"📊 EXTRACTION STATISTICS:")
        print(f"   Total Hotels: {total}")
        print(f"   With Names: {with_names} ({with_names/total*100:.1f}%)")
        print(f"   With Prices: {with_prices} ({with_prices/total*100:.1f}%)")
        print(f"   With Ratings: {with_ratings} ({with_ratings/total*100:.1f}%)")
        print(f"   With Categories: {with_categories} ({with_categories/total*100:.1f}%)")  # Key metric
        print(f"   With Locations: {with_locations} ({with_locations/total*100:.1f}%)")
        
        # Debug info
        print(f"\n🔧 DEBUG INFO:")
        print(f"   Page Loads: {self.debug_info['page_loads']}")
        print(f"   Selectors Tried: {len(self.debug_info['selectors_tried'])}")
        print(f"   Errors: {len(self.debug_info['errors'])}")
        print(f"   Hotels Per Iteration: {self.debug_info['hotels_found_per_iteration']}")
        
        # Category examples
        categories = [h['category'] for h in self.hotels_data if h['category']]
        if categories:
            unique_categories = list(set(categories))[:10]
            print(f"\n🏷️  CATEGORY EXAMPLES (Found {len(unique_categories)} unique types):")
            for i, cat in enumerate(unique_categories, 1):
                print(f"   {i}. {cat}")
        
        # Sample hotels
        print(f"\n🏨 SAMPLE HOTELS:")
        for i, hotel in enumerate(self.hotels_data[:3], 1):
            print(f"   {i}. {hotel['name'][:40]}...")
            print(f"      Category: {hotel['category'][:30]}...")
            print(f"      Price: {hotel['price'][:20]}...")
            print(f"      Rating: {hotel['rating']}")
            print()
    
    def cleanup(self):
        """Enhanced cleanup with debug info"""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("Driver closed successfully")
            except Exception as e:
                logger.error(f"Error closing driver: {str(e)}")

def main():
    """Main execution with enhanced error handling"""
    url = "https://www.agoda.com/en-in/search?guid=ac34b805-fbbb-4a54-91f6-72bd44251297&asq=oSBZUdCJkTqIcAJrG1AX8Jufa9Vwpz6XltTHq4n%2B9gNpSLc%2BT%2BpB%2F8FnmmA8sOyAJ0WZY5hpLWEr%2Fk8qr78gW4DMS7e7llLtqq76yKsoLJ2OoQ3gw8ln%2FUAwfEcSpHO4IoT8r2EKxXsqX%2FNiA5fxsgqQMycviD3CIWSJVwpQ8sqLB7kVtS1F64bq7yiJpY541pwsBzifP5NpR6wrJ1u54kHb%2BKC2e3zym6tmyvlzCzM%3D&city=10863&tick=638881978745&locale=en-in&ckuid=0782016a-40d3-4e7a-86a4-8cab9dacec41&prid=0&gclid=Cj0KCQjw-NfDBhDyARIsAD-ILeBXva5TJhq-jGK3Si0BOfvtLo82iIstmv4-XMoqfU56Mshxz_UezUkaAhwMEALw_wcB&currency=INR&correlationId=55168ae7-8bc1-4224-a8eb-86ba246be729&analyticsSessionId=-1950121884218971931&pageTypeId=1&realLanguageId=15&languageId=1&origin=IN&stateCode=WB&cid=1922885&tag=6f147157-60b8-459f-af1a-9935d44970e9&userId=0782016a-40d3-4e7a-86a4-8cab9dacec41&whitelabelid=1&loginLvl=0&storefrontId=3&currencyId=27&currencyCode=INR&htmlLanguage=en-in&cultureInfoName=en-in&machineName=sg-pc-6h-acm-web-user-8697c4cd7c-gmgqx&trafficGroupId=5&trafficSubGroupId=122&aid=82361&useFullPageLogin=true&cttp=4&isRealUser=true&mode=production&browserFamily=Chrome&cdnDomain=agoda.net&checkIn=2025-08-12&checkOut=2025-08-13&rooms=1&adults=2&children=0&priceCur=INR&los=1&textToSearch=Darjeeling&travellerType=1&familyMode=off&ds=cgN73pCK5wrspJ7h&productType=-1"
    
    scraper = AgodaScraperRobust()
    
    try:
        logger.info("🚀 Starting robust Agoda scraping...")
        success = scraper.scrape_hotels_robust(url, max_iterations=3)
        
        if success:
            logger.info("✅ Scraping completed successfully!")
            scraper.save_data_enhanced()
        else:
            logger.error("❌ Scraping failed!")
            print("\n🔍 TROUBLESHOOTING TIPS:")
            print("1. Check debug files created in the workspace")
            print("2. Verify the URL is accessible")
            print("3. Try with a different Agoda search URL")
            print("4. Check if Agoda is blocking automated access")
            
    except KeyboardInterrupt:
        logger.info("Scraping interrupted by user")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
    finally:
        scraper.cleanup()

if __name__ == "__main__":
    main()