from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time
import csv
import random
import json
import re
from urllib.parse import urljoin, urlparse

class AgodaUltimateScraper:
    def __init__(self, search_url):
        self.search_url = search_url
        self.base_url = "https://www.agoda.com"
        self.all_hotels = []
        self.driver = None
        
    def create_stealth_driver(self):
        """Create Firefox driver with maximum stealth and incognito mode"""
        print("[STEALTH] Initializing Firefox in INCOGNITO MODE...")
        
        options = Options()
        
        # INCOGNITO MODE - Your excellent suggestion!
        options.add_argument("--private-window")
        options.add_argument("--private")
        
        # Maximum stealth configuration
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-plugins")
        options.add_argument("--disable-images")  # Faster loading
        
        # Stealth preferences
        options.set_preference("dom.webdriver.enabled", False)
        options.set_preference("useAutomationExtension", False)
        options.set_preference("general.useragent.override", 
                              "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
        
        # Performance optimization
        options.set_preference("network.http.pipelining", True)
        options.set_preference("network.http.proxy.pipelining", True)
        options.set_preference("network.http.pipelining.maxrequests", 8)
        options.set_preference("content.notify.interval", 500000)
        options.set_preference("content.notify.ontimer", True)
        options.set_preference("content.switch.threshold", 250000)
        
        # Disable images for speed (proxy-like behavior)
        options.set_preference("permissions.default.image", 2)
        
        # Create driver
        self.driver = webdriver.Firefox(options=options)
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        print("[SUCCESS] Firefox incognito mode initialized successfully!")
        return self.driver
    
    def smart_wait(self, selector, timeout=15, multiple=False):
        """Smart waiting with multiple strategies"""
        try:
            if multiple:
                return WebDriverWait(self.driver, timeout).until(
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, selector))
                )
            else:
                return WebDriverWait(self.driver, timeout).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                )
        except TimeoutException:
            return None
    
    def close_popups(self):
        """Close any popups or overlays"""
        popup_selectors = [
            'button[aria-label="Close"]',
            '.close-button',
            '[data-selenium="close-button"]',
            'button[data-testid="close-button"]',
            '.modal-close',
            '.popup-close',
            '[data-testid="modal-close"]'
        ]
        
        for selector in popup_selectors:
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                for element in elements:
                    if element.is_displayed():
                        element.click()
                        time.sleep(0.5)
            except:
                continue
    
    def progressive_scroll(self, iterations=10):
        """Optimized scrolling to load content"""
        last_height = self.driver.execute_script("return document.body.scrollHeight")
        
        for i in range(iterations):
            # Scroll in small increments
            scroll_position = (i + 1) * (1.0 / iterations)
            self.driver.execute_script(f"window.scrollTo(0, document.body.scrollHeight * {scroll_position});")
            
            # Random human-like delays
            time.sleep(random.uniform(1.5, 2.5))
            
            # Check if new content loaded
            new_height = self.driver.execute_script("return document.body.scrollHeight")
            if new_height != last_height:
                last_height = new_height
                time.sleep(1)
    
    def extract_basic_hotel_info(self, card):
        """Extract basic hotel information from search results using correct selector"""
        # Hotel name and link using YOUR SPECIFIC SELECTOR
        name_elem = card.select_one('a[data-testid="property-name-link"]')
        if not name_elem:
            # Fallback selectors
            name_elem = card.select_one('a.TextLink__TextLinkStyled-sc-upxc4y-1.iA-DeZb')
            if not name_elem:
                name_elem = card.select_one('a[data-selenium="hotel-name"]')
        
        if not name_elem:
            return None
            
        name = name_elem.get_text(strip=True)
        hotel_link = name_elem.get('href')
        
        if not name or not hotel_link:
            return None
        
        # Clean promotional text
        name = re.sub(r'(Limited time offer|Expires in|SUPER WEDNESDAY|NIGHT OWL|MONSOON|BOOK EARLY).*$', '', name, flags=re.IGNORECASE).strip()
        
        # Extract price
        price = "N/A"
        price_elem = card.select_one('span[data-selenium="display-price"]')
        if not price_elem:
            price_elem = card.select_one('.PropertyCardPrice__Value')
        if price_elem:
            price = price_elem.get_text(strip=True)
        
        # Extract location
        location = "N/A"
        location_elem = card.select_one('[data-selenium="hotel-location"]')
        if location_elem:
            location = location_elem.get_text(strip=True)
        
        # Extract rating
        rating = "N/A"
        rating_elem = card.select_one('span[data-selenium="hotel-rating"]')
        if rating_elem:
            rating = rating_elem.get_text(strip=True)
        
        # Construct full URL
        if hotel_link.startswith('/'):
            hotel_url = urljoin(self.base_url, hotel_link)
        else:
            hotel_url = hotel_link
            
        return {
            'name': name,
            'price': price,
            'location': location,
            'rating': rating,
            'url': hotel_url
        }
    
    def extract_room_categories(self):
        """Extract room categories using YOUR SPECIFIC SELECTORS"""
        try:
            print("  -> [ROOMS] Extracting room categories...")
            
            # Wait for page to load
            time.sleep(3)
            
            # Close any popups first
            self.close_popups()
            
            # Click "View All Rooms" button using YOUR SPECIFIC SELECTOR
            try:
                view_all_btn = self.driver.find_element(By.CSS_SELECTOR, 'button[id="property-room-grid-root-tab-2"]')
                if view_all_btn.is_displayed() and view_all_btn.is_enabled():
                    print("  -> [ACTION] Clicking 'View All Rooms' button...")
                    self.driver.execute_script("arguments[0].scrollIntoView(true);", view_all_btn)
                    time.sleep(1)
                    view_all_btn.click()
                    time.sleep(3)
                    print("  -> [SUCCESS] Clicked View All Rooms")
            except Exception as e:
                print(f"  -> [WARNING] View All Rooms button not found: {e}")
            
            # Scroll to load all rooms
            self.progressive_scroll(iterations=5)
            
            # Extract room categories using YOUR SPECIFIC SELECTOR
            soup = BeautifulSoup(self.driver.page_source, "html.parser")
            room_categories = []
            
            # YOUR SPECIFIC ROOM CATEGORY SELECTOR
            room_containers = soup.select('div.af0e5-box.af0e5-fill-inherit.af0e5-text-inherit.af0e5-items-center.af0e5-flex.af0e5-justify-center.af0e5-relative.af0e5-snap-start.af0e5-px-4')
            
            # Extract room names from containers
            for container in room_containers:
                room_text = container.get_text(strip=True)
                
                # Filter out invalid entries
                if (not room_text or len(room_text) < 3 or len(room_text) > 100 or
                    any(skip in room_text.lower() for skip in ['select', 'choose', 'book', 'price', 'available', 'guest', 'check', 'view'])):
                    continue
                
                # Clean promotional text
                room_text = re.sub(r'(Limited time offer|Expires in|SUPER WEDNESDAY|NIGHT OWL).*$', '', room_text, flags=re.IGNORECASE).strip()
                
                if room_text and room_text not in room_categories:
                    room_categories.append(room_text)
            
            # Alternative selectors for room categories
            if not room_categories:
                print("  -> [FALLBACK] Trying alternative room selectors...")
                
                # Try other common room selectors
                alt_selectors = [
                    '.RoomGrid-titleCounterNormal',
                    '[data-selenium="masterroom-title-name"]',
                    '.room-name',
                    '.room-title',
                    '.masterroom-name'
                ]
                
                for selector in alt_selectors:
                    room_elements = soup.select(selector)
                    for elem in room_elements:
                        room_text = elem.get_text(strip=True)
                        if (room_text and 5 <= len(room_text) <= 80 and 
                            room_text not in room_categories and
                            not any(skip in room_text.lower() for skip in ['select', 'choose', 'book', 'price'])):
                            room_categories.append(room_text)
                    
                    if room_categories:
                        break
            
            # Limit to reasonable number
            room_categories = room_categories[:10]
            
            print(f"  -> [SUCCESS] Found {len(room_categories)} room categories: {room_categories}")
            return room_categories
            
        except Exception as e:
            print(f"  -> [ERROR] Error extracting room categories: {e}")
            return []
    
    def extract_reviews(self):
        """Extract reviews using YOUR SPECIFIC SELECTORS"""
        try:
            print("  -> [REVIEWS] Extracting hotel reviews...")
            
            # Scroll to find reviews section
            self.progressive_scroll(iterations=8)
            
            # Parse page content
            soup = BeautifulSoup(self.driver.page_source, "html.parser")
            reviews = []
            
            # YOUR SPECIFIC REVIEW SELECTOR
            review_containers = soup.select('div.af0e5-box.af0e5-fill-inherit.af0e5-text-inherit.af0e5-items-center.af0e5-flex.af0e5-justify-center.af0e5-relative.af0e5-snap-start.af0e5-px-4')
            
            # Look for review bubbles within containers
            for container in review_containers:
                review_bubbles = container.select('.Review-comment-bubble')
                for bubble in review_bubbles:
                    review_text = bubble.get_text(strip=True)
                    
                    # Validate review text
                    if (review_text and 10 <= len(review_text) <= 500 and
                        review_text not in reviews):
                        reviews.append(review_text)
            
            # Alternative review selectors if primary doesn't work
            if not reviews:
                print("  -> [FALLBACK] Trying alternative review selectors...")
                
                alt_review_selectors = [
                    '.Review-comment-bubble',
                    '[data-testid="review-comment"]',
                    '.review-comment',
                    '.guest-review-text',
                    '.review-text',
                    '.comment-text'
                ]
                
                for selector in alt_review_selectors:
                    review_elements = soup.select(selector)
                    for elem in review_elements:
                        review_text = elem.get_text(strip=True)
                        if (review_text and 10 <= len(review_text) <= 500 and
                            review_text not in reviews):
                            reviews.append(review_text)
                    
                    if reviews:
                        break
            
            # Limit to reasonable number
            reviews = reviews[:20]
            
            print(f"  -> [SUCCESS] Found {len(reviews)} reviews")
            return reviews
            
        except Exception as e:
            print(f"  -> [ERROR] Error extracting reviews: {e}")
            return []
    
    def extract_detailed_hotel_info(self, hotel_info):
        """Extract detailed information from individual hotel page"""
        try:
            print(f"\n  🏨 [HOTEL] Processing: {hotel_info['name']}")
            print(f"  🔗 [URL] Visiting: {hotel_info['url']}")
            
            # Navigate to hotel page
            self.driver.get(hotel_info['url'])
            
            # Wait for page to load
            time.sleep(random.uniform(3, 5))
            
            # Close popups
            self.close_popups()
            
            # Extract room categories
            room_categories = self.extract_room_categories()
            
            # Extract reviews
            reviews = self.extract_reviews()
            
            # Create enhanced hotel data
            enhanced_hotel = {
                "name": hotel_info['name'],
                "price": hotel_info['price'],
                "location": hotel_info['location'],
                "rating": hotel_info['rating'],
                "url": hotel_info['url'],
                "room_categories": ", ".join(room_categories) if room_categories else "N/A",
                "total_room_types": len(room_categories),
                "reviews": " | ".join(reviews[:5]) if reviews else "N/A",  # Top 5 reviews
                "total_reviews_found": len(reviews)
            }
            
            print(f"  ✅ [COMPLETE] {hotel_info['name']} | {len(room_categories)} rooms | {len(reviews)} reviews")
            return enhanced_hotel
            
        except Exception as e:
            print(f"  ❌ [ERROR] Error processing {hotel_info['name']}: {e}")
            # Return basic info if detailed extraction fails
            return {
                "name": hotel_info['name'],
                "price": hotel_info['price'],
                "location": hotel_info['location'],
                "rating": hotel_info['rating'],
                "url": hotel_info['url'],
                "room_categories": "Error extracting",
                "total_room_types": 0,
                "reviews": "Error extracting",
                "total_reviews_found": 0
            }
    
    def navigate_back_safely(self):
        """Navigate back to search results safely"""
        try:
            print("  🔙 [NAVIGATE] Returning to search results...")
            self.driver.back()
            time.sleep(random.uniform(3, 5))
            
            # Wait for search results to reload
            self.smart_wait('li[data-selenium="hotel-item"], div[data-selenium="hotel-item"]', timeout=15)
            
        except Exception as e:
            print(f"  ⚠️ [WARNING] Navigation error: {e}")
            # Fallback: refresh the search page
            print("  🔄 [FALLBACK] Refreshing search page...")
            self.driver.get(self.search_url)
            time.sleep(5)
    
    def scrape_page(self, page_num):
        """Scrape a single page of results"""
        print(f"\n📄 [PAGE] Scraping page {page_num}...")
        
        # Progressive scrolling to load all content
        self.progressive_scroll()
        
        # Parse page content
        soup = BeautifulSoup(self.driver.page_source, "html.parser")
        
        # Find hotel cards
        hotel_cards = soup.select('li[data-selenium="hotel-item"]')
        if not hotel_cards:
            hotel_cards = soup.select('div[data-selenium="hotel-item"]')
        
        print(f"🏨 [FOUND] {len(hotel_cards)} hotels on page {page_num}")
        
        page_hotels = []
        
        for i, card in enumerate(hotel_cards):
            try:
                # Extract basic info from search results
                hotel_info = self.extract_basic_hotel_info(card)
                if not hotel_info:
                    print(f"  ⚠️ [SKIP] Could not extract basic info for hotel {i+1}")
                    continue
                
                print(f"\n🔍 [PROCESSING] Hotel {i+1}/{len(hotel_cards)}")
                
                # Extract detailed info by visiting hotel page
                detailed_hotel = self.extract_detailed_hotel_info(hotel_info)
                
                # Navigate back to search results
                self.navigate_back_safely()
                
                page_hotels.append(detailed_hotel)
                
                # Respectful delay between hotels
                time.sleep(random.uniform(2, 4))
                
            except Exception as e:
                print(f"❌ [ERROR] Error processing hotel {i+1}: {e}")
                continue
        
        return page_hotels
    
    def try_next_page(self):
        """Try to navigate to next page"""
        next_selectors = [
            'button[data-selenium="pagination-next"]',
            'button.pagination2__next',
            'button[aria-label="Next page"]',
            '.Buttonstyled__ButtonStyled-sc-5gjk6l-0.jyyvGo.btn.pagination2__next'
        ]
        
        for selector in next_selectors:
            try:
                next_btn = self.driver.find_element(By.CSS_SELECTOR, selector)
                if (next_btn.is_displayed() and next_btn.is_enabled() and 
                    "disabled" not in next_btn.get_attribute("class")):
                    
                    self.driver.execute_script("arguments[0].scrollIntoView(true);", next_btn)
                    time.sleep(1)
                    next_btn.click()
                    time.sleep(random.uniform(4, 6))
                    return True
            except:
                continue
        return False
    
    def run(self):
        """Main scraping execution"""
        print("=" * 80)
        print("🚀 AGODA ULTIMATE SCRAPER - ENHANCED VERSION")
        print("📋 Features: Hotel URLs + Room Categories + Reviews")
        print("=" * 80)
        
        # Create stealth driver
        self.create_stealth_driver()
        
        try:
            # Navigate to search page
            print(f"🌐 [NAVIGATE] Loading: {self.search_url}")
            self.driver.get(self.search_url)
            time.sleep(5)
            
            # Close popups
            self.close_popups()
            
            # Wait for initial content
            if not self.smart_wait('li[data-selenium="hotel-item"], div[data-selenium="hotel-item"]', timeout=20):
                print("❌ [ERROR] No hotel listings found!")
                return
            
            page_num = 1
            
            while True:
                # Scrape current page
                page_hotels = self.scrape_page(page_num)
                self.all_hotels.extend(page_hotels)
                
                print(f"\n📊 [PROGRESS] Page {page_num} complete: {len(page_hotels)} hotels processed")
                
                # Try to go to next page
                if not self.try_next_page():
                    print("🏁 [END] No more pages available")
                    break
                
                page_num += 1
                
                # Safety limit
                if page_num > 10:  # Reasonable limit for testing
                    print("⚠️ [LIMIT] Reached maximum page limit")
                    break
            
            # Save results
            self.save_results()
            
        except Exception as e:
            print(f"💥 [CRITICAL] Critical error: {e}")
            
        finally:
            if self.driver:
                self.driver.quit()
                print("🔒 [CLOSED] Browser closed")
    
    def save_results(self):
        """Save scraped results to files"""
        # Remove duplicates
        unique_hotels = []
        seen_names = set()
        
        for hotel in self.all_hotels:
            if hotel['name'] not in seen_names:
                unique_hotels.append(hotel)
                seen_names.add(hotel['name'])
        
        print("\n" + "=" * 80)
        print("🎉 SCRAPING COMPLETE!")
        print("=" * 80)
        
        # Save CSV with enhanced fields
        csv_filename = "agoda_ultimate_enhanced_results.csv"
        with open(csv_filename, "w", newline="", encoding="utf-8") as f:
            fieldnames = ["name", "price", "location", "rating", "url", 
                         "room_categories", "total_room_types", "reviews", "total_reviews_found"]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(unique_hotels)
        
        # Save JSON
        json_filename = "agoda_ultimate_enhanced_results.json"
        with open(json_filename, "w", encoding="utf-8") as f:
            json.dump(unique_hotels, f, indent=2, ensure_ascii=False)
        
        # Calculate statistics
        total_rooms = sum(hotel.get("total_room_types", 0) for hotel in unique_hotels)
        total_reviews = sum(hotel.get("total_reviews_found", 0) for hotel in unique_hotels)
        avg_rooms = total_rooms / len(unique_hotels) if unique_hotels else 0
        avg_reviews = total_reviews / len(unique_hotels) if unique_hotels else 0
        
        print(f"📊 [STATISTICS]")
        print(f"   🏨 Total hotels: {len(unique_hotels)}")
        print(f"   🏠 Total room categories: {total_rooms}")
        print(f"   💬 Total reviews found: {total_reviews}")
        print(f"   📈 Average rooms per hotel: {avg_rooms:.1f}")
        print(f"   📈 Average reviews per hotel: {avg_reviews:.1f}")
        
        print(f"\n💾 [FILES SAVED]")
        print(f"   📄 CSV: {csv_filename}")
        print(f"   📄 JSON: {json_filename}")
        print("=" * 80)

def main():
    """Main function to run the scraper"""
    # Your Agoda search URL
    search_url = "https://www.agoda.com/en-in/search?guid=ac34b805-fbbb-4a54-91f6-72bd44251297&asq=oSBZUdCJkTqIcAJrG1AX8Jufa9Vwpz6XltTHq4n%2B9gNpSLc%2BT%2BpB%2F8FnmmA8sOyAJ0WZY5hpLWEr%2Fk8qr78gW4DMS7e7llLtqq76yKsoLJ2OoQ3gw8ln%2FUAwfEcSpHO4IoT8r2EKxXsqX%2FNiA5fxsgqQMycviD3CIWSJVwpQ8sqLB7kVtS1F64bq7yiJpY541pwsBzifP5NpR6wrJ1u54kHb%2BKC2e3zym6tmyvlzCzM%3D&city=10863&tick=638881978745&locale=en-in&ckuid=0782016a-40d3-4e7a-86a4-8cab9dacec41&prid=0&gclid=Cj0KCQjw-NfDBhDyARIsAD-ILeBXva5TJhq-jGK3Si0BOfvtLo82iIstmv4-XMoqfU56Mshxz_UezUkaAhwMEALw_wcB&currency=INR&correlationId=55168ae7-8bc1-4224-a8eb-86ba246be729&analyticsSessionId=-1950121884218971931&pageTypeId=1&realLanguageId=15&languageId=1&origin=IN&stateCode=WB&cid=1922885&tag=6f147157-60b8-459f-af1a-9935d44970e9&userId=0782016a-40d3-4e7a-86a4-8cab9dacec41&whitelabelid=1&loginLvl=0&storefrontId=3&currencyId=27&currencyCode=INR&htmlLanguage=en-in&cultureInfoName=en-in&machineName=sg-pc-6h-acm-web-user-8697c4cd7c-gmgqx&trafficGroupId=5&trafficSubGroupId=122&aid=82361&useFullPageLogin=true&cttp=4&isRealUser=true&mode=production&browserFamily=Chrome&cdnDomain=agoda.net&checkIn=2025-08-12&checkOut=2025-08-13&rooms=1&adults=2&children=0&priceCur=INR&los=1&textToSearch=Darjeeling&travellerType=1&familyMode=off&ds=cgN73pCK5wrspJ7h&productType=-1"
    
    print("🚀 Agoda Ultimate Scraper - Enhanced Edition")
    print("📋 Extracts: Hotel URLs + Room Categories + Reviews")
    print("🔧 Uses your specific selectors for maximum accuracy")
    print("-" * 60)
    
    scraper = AgodaUltimateScraper(search_url)
    scraper.run()

if __name__ == "__main__":
    main()