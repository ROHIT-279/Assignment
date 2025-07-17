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

class AgodaEnhancedScraper:
    def __init__(self, search_url):
        self.search_url = search_url
        self.base_url = "https://www.agoda.com"
        self.all_hotels = []
        self.driver = None
        
    def create_stealth_driver(self):
        """Create Firefox driver with maximum stealth and incognito mode"""
        print("[STEALTH] Initializing Firefox in INCOGNITO MODE...")
        
        options = Options()
        
        # INCOGNITO MODE
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
            '.popup-close'
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
        """Extract basic hotel information from search results using correct selectors"""
        # Hotel name and link using the correct testid selector
        name_elem = card.select_one('a[data-testid="property-name-link"]')
        if not name_elem:
            # Fallback to previous selector
            name_elem = card.select_one('a.TextLink__TextLinkStyled-sc-upxc4y-1.iA-DeZb')
        
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
        """Extract room categories using the provided selector"""
        try:
            # Wait for room content to load
            time.sleep(2)
            
            # Click "View All Rooms" button using the provided selector
            try:
                view_all_btn = self.driver.find_element(By.CSS_SELECTOR, 'button[id="property-room-grid-root-tab-2"]')
                if view_all_btn.is_displayed() and view_all_btn.is_enabled():
                    print("    [ACTION] Clicking 'View All Rooms'...")
                    self.driver.execute_script("arguments[0].scrollIntoView(true);", view_all_btn)
                    time.sleep(1)
                    view_all_btn.click()
                    time.sleep(3)
            except Exception as e:
                print(f"    [WARNING] View All Rooms button not found: {e}")
            
            # Scroll to load room content
            self.progressive_scroll(iterations=5)
            
            # Extract room categories using the provided selector
            soup = BeautifulSoup(self.driver.page_source, "html.parser")
            room_categories = []
            
            # Use the provided selector for room categories
            room_elements = soup.select('.af0e5-box.af0e5-fill-inherit.af0e5-text-inherit.af0e5-items-center.af0e5-flex.af0e5-justify-center.af0e5-relative.af0e5-snap-start.af0e5-px-4')
            
            # Also try alternative selectors
            if not room_elements:
                room_elements = soup.select('.RoomGrid-titleCounterNormal')
            
            if not room_elements:
                room_elements = soup.select('[data-testid="room-type-name"]')
            
            # Extract and clean room names
            for room_elem in room_elements:
                room_text = room_elem.get_text(strip=True)
                
                # Skip invalid entries
                if (not room_text or len(room_text) < 3 or len(room_text) > 100 or
                    any(skip in room_text.lower() for skip in ['select', 'choose', 'book', 'price', 'available', 'guest', 'view all'])):
                    continue
                
                # Clean and validate
                room_text = re.sub(r'(Limited time offer|Expires in|SUPER WEDNESDAY|NIGHT OWL).*$', '', room_text, flags=re.IGNORECASE).strip()
                
                if room_text and room_text not in room_categories:
                    room_categories.append(room_text)
            
            # Fallback: Look for room-related keywords in page content
            if not room_categories:
                all_text = soup.get_text()
                potential_rooms = re.findall(r'[A-Z][a-z\s]*(?:Room|Suite|Deluxe|Standard|Premium|Executive|King|Queen|Twin|Double)[A-Za-z\s]*', all_text)
                
                for room in potential_rooms[:5]:  # Limit to 5
                    room = room.strip()
                    if 10 <= len(room) <= 80 and room not in room_categories:
                        room_categories.append(room)
            
            print(f"    [SUCCESS] Found {len(room_categories)} room types: {room_categories}")
            return room_categories
            
        except Exception as e:
            print(f"    [ERROR] Error extracting rooms: {e}")
            return []
    
    def extract_reviews(self):
        """Extract reviews using the provided selector"""
        try:
            print("    [ACTION] Extracting reviews...")
            
            # Navigate to reviews tab if it exists
            try:
                review_tab_selectors = [
                    'button[data-testid="reviews-tab"]',
                    'a[href*="reviews"]',
                    'button[id*="review"]',
                    '.af0e5-box.af0e5-fill-inherit.af0e5-text-inherit.af0e5-items-center.af0e5-flex.af0e5-justify-center.af0e5-relative.af0e5-snap-start.af0e5-px-4'
                ]
                
                for selector in review_tab_selectors:
                    try:
                        review_tab = self.driver.find_element(By.CSS_SELECTOR, selector)
                        if review_tab.is_displayed() and 'review' in review_tab.get_attribute('innerText').lower():
                            print("    [ACTION] Clicking reviews tab...")
                            self.driver.execute_script("arguments[0].scrollIntoView(true);", review_tab)
                            time.sleep(1)
                            review_tab.click()
                            time.sleep(3)
                            break
                    except:
                        continue
            except Exception as e:
                print(f"    [WARNING] Reviews tab not found: {e}")
            
            # Scroll to load reviews
            self.progressive_scroll(iterations=3)
            
            # Extract reviews using the provided selector
            soup = BeautifulSoup(self.driver.page_source, "html.parser")
            reviews = []
            
            # Use the provided selector for reviews
            review_elements = soup.select('.Review-comment-bubble')
            
            # Alternative selectors for reviews
            if not review_elements:
                review_elements = soup.select('[data-testid="review-content"]')
            
            if not review_elements:
                review_elements = soup.select('.review-text, .review-content, .comment-text')
            
            # Extract review text
            for review_elem in review_elements:
                review_text = review_elem.get_text(strip=True)
                
                # Skip invalid reviews
                if (not review_text or len(review_text) < 10 or len(review_text) > 500):
                    continue
                
                # Clean review text
                review_text = re.sub(r'\s+', ' ', review_text).strip()
                
                if review_text and review_text not in reviews:
                    reviews.append(review_text)
                
                # Limit to top 10 reviews for performance
                if len(reviews) >= 10:
                    break
            
            print(f"    [SUCCESS] Found {len(reviews)} reviews")
            return reviews
            
        except Exception as e:
            print(f"    [ERROR] Error extracting reviews: {e}")
            return []
    
    def extract_detailed_hotel_info(self, hotel_info):
        """Extract detailed hotel information including room categories and reviews"""
        try:
            print(f"  -> Visiting: {hotel_info['name']}")
            self.driver.get(hotel_info['url'])
            
            # Wait for page to load
            time.sleep(3)
            self.close_popups()
            
            # Extract room categories
            room_categories = self.extract_room_categories()
            
            # Extract reviews
            reviews = self.extract_reviews()
            
            return {
                'room_categories': room_categories,
                'reviews': reviews
            }
            
        except Exception as e:
            print(f"  [ERROR] Error extracting detailed info: {e}")
            return {
                'room_categories': [],
                'reviews': []
            }
    
    def navigate_back_safely(self):
        """Navigate back to search results safely"""
        try:
            self.driver.back()
            time.sleep(random.uniform(2, 4))
            
            # Wait for search results to reload
            self.smart_wait('li[data-selenium="hotel-item"], div[data-selenium="hotel-item"]', timeout=10)
            
        except Exception as e:
            print(f"  [WARNING] Navigation error: {e}")
            # Fallback: refresh the search page
            self.driver.get(self.search_url)
            time.sleep(3)
    
    def scrape_page(self, page_num):
        """Scrape a single page of results"""
        print(f"\n[PAGE] Scraping page {page_num}...")
        
        # Progressive scrolling to load all content
        self.progressive_scroll()
        
        # Parse page content
        soup = BeautifulSoup(self.driver.page_source, "html.parser")
        
        # Find hotel cards
        hotel_cards = soup.select('li[data-selenium="hotel-item"]')
        if not hotel_cards:
            hotel_cards = soup.select('div[data-selenium="hotel-item"]')
        
        print(f"[HOTELS] Found {len(hotel_cards)} hotels on page {page_num}")
        
        page_hotels = []
        
        for i, card in enumerate(hotel_cards):
            try:
                # Extract basic info
                hotel_info = self.extract_basic_hotel_info(card)
                if not hotel_info:
                    continue
                
                print(f"\n[HOTEL] Processing hotel {i+1}/{len(hotel_cards)}: {hotel_info['name']}")
                
                # Extract detailed information (room categories and reviews)
                detailed_info = self.extract_detailed_hotel_info(hotel_info)
                
                # Navigate back to search results
                self.navigate_back_safely()
                
                # Create final hotel data
                hotel_data = {
                    "name": hotel_info['name'],
                    "price": hotel_info['price'],
                    "location": hotel_info['location'],
                    "rating": hotel_info['rating'],
                    "url": hotel_info['url'],
                    "room_categories": ", ".join(detailed_info['room_categories']) if detailed_info['room_categories'] else "N/A",
                    "total_room_types": len(detailed_info['room_categories']),
                    "reviews": " | ".join(detailed_info['reviews'][:5]) if detailed_info['reviews'] else "N/A",  # Top 5 reviews
                    "total_reviews_found": len(detailed_info['reviews'])
                }
                
                page_hotels.append(hotel_data)
                print(f"[ADDED] Added: {hotel_info['name']} | {len(detailed_info['room_categories'])} room types | {len(detailed_info['reviews'])} reviews")
                
                # Respectful delay
                time.sleep(random.uniform(2, 4))
                
            except Exception as e:
                print(f"[ERROR] Error processing hotel {i+1}: {e}")
                continue
        
        return page_hotels
    
    def try_next_page(self):
        """Try to navigate to next page"""
        next_selectors = [
            'button[data-selenium="pagination-next"]',
            'button.pagination2__next',
            'button[aria-label="Next page"]'
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
        print("=" * 60)
        print("ENHANCED AGODA SCRAPER WITH ROOM CATEGORIES & REVIEWS")
        print("=" * 60)
        
        # Create stealth driver
        self.create_stealth_driver()
        
        try:
            # Navigate to search page
            print(f"[NAVIGATE] Navigating to: {self.search_url}")
            self.driver.get(self.search_url)
            time.sleep(3)
            
            # Close popups
            self.close_popups()
            
            # Wait for initial content
            if not self.smart_wait('li[data-selenium="hotel-item"], div[data-selenium="hotel-item"]', timeout=20):
                print("[ERROR] No hotel listings found!")
                return
            
            page_num = 1
            
            while True:
                # Scrape current page
                page_hotels = self.scrape_page(page_num)
                self.all_hotels.extend(page_hotels)
                
                # Try to go to next page
                if not self.try_next_page():
                    print("[END] No more pages available")
                    break
                
                page_num += 1
                
                # Safety limit
                if page_num > 25:
                    print("[LIMIT] Reached maximum page limit")
                    break
            
            # Save results
            self.save_results()
            
        except Exception as e:
            print(f"[CRITICAL] Critical error: {e}")
            
        finally:
            if self.driver:
                self.driver.quit()
                print("[CLOSED] Browser closed")
    
    def save_results(self):
        """Save scraped results to files"""
        # Remove duplicates
        unique_hotels = []
        seen_names = set()
        
        for hotel in self.all_hotels:
            if hotel['name'] not in seen_names:
                unique_hotels.append(hotel)
                seen_names.add(hotel['name'])
        
        print("\n" + "=" * 60)
        print("SCRAPING COMPLETE!")
        print("=" * 60)
        print(f"[RESULTS] Total unique hotels: {len(unique_hotels)}")
        
        # Save CSV
        fieldnames = ["name", "price", "location", "rating", "url", "room_categories", "total_room_types", "reviews", "total_reviews_found"]
        with open("agoda_enhanced_results.csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(unique_hotels)
        
        # Save JSON
        with open("agoda_enhanced_results.json", "w", encoding="utf-8") as f:
            json.dump(unique_hotels, f, indent=2, ensure_ascii=False)
        
        # Statistics
        total_rooms = sum(hotel["total_room_types"] for hotel in unique_hotels)
        total_reviews = sum(hotel["total_reviews_found"] for hotel in unique_hotels)
        avg_rooms = total_rooms / len(unique_hotels) if unique_hotels else 0
        avg_reviews = total_reviews / len(unique_hotels) if unique_hotels else 0
        
        print("\n" + "=" * 60)
        print("FINAL STATISTICS")
        print("=" * 60)
        print(f"[HOTELS] Total hotels scraped: {len(unique_hotels)}")
        print(f"[ROOMS] Total room categories: {total_rooms}")
        print(f"[REVIEWS] Total reviews extracted: {total_reviews}")
        print(f"[AVERAGE] Average rooms per hotel: {avg_rooms:.1f}")
        print(f"[AVERAGE] Average reviews per hotel: {avg_reviews:.1f}")
        print("\n" + "=" * 60)
        print("FILES SAVED")
        print("=" * 60)
        print("  - agoda_enhanced_results.csv")
        print("  - agoda_enhanced_results.json")
        print("=" * 60)

def main():
    """Main function to run the scraper"""
    # Replace with your actual Agoda search URL
    search_url = "https://www.agoda.com/en-in/search?guid=ac34b805-fbbb-4a54-91f6-72bd44251297&asq=oSBZUdCJkTqIcAJrG1AX8Jufa9Vwpz6XltTHq4n%2B9gNpSLc%2BT%2BpB%2F8FnmmA8sOyAJ0WZY5hpLWEr%2Fk8qr78gW4DMS7e7llLtqq76yKsoLJ2OoQ3gw8ln%2FUAwfEcSpHO4IoT8r2EKxXsqX%2FNiA5fxsgqQMycviD3CIWSJVwpQ8sqLB7kVtS1F64bq7yiJpY541pwsBzifP5NpR6wrJ1u54kHb%2BKC2e3zym6tmyvlzCzM%3D&city=10863&tick=638881978745&locale=en-in&ckuid=0782016a-40d3-4e7a-86a4-8cab9dacec41&prid=0&gclid=Cj0KCQjw-NfDBhDyARIsAD-ILeBXva5TJhq-jGK3Si0BOfvtLo82iIstmv4-XMoqfU56Mshxz_UezUkaAhwMEALw_wcB&currency=INR&correlationId=55168ae7-8bc1-4224-a8eb-86ba246be729&analyticsSessionId=-1950121884218971931&pageTypeId=1&realLanguageId=15&languageId=1&origin=IN&stateCode=WB&cid=1922885&tag=6f147157-60b8-459f-af1a-9935d44970e9&userId=0782016a-40d3-4e7a-86a4-8cab9dacec41&whitelabelid=1&loginLvl=0&storefrontId=3&currencyId=27&currencyCode=INR&htmlLanguage=en-in&cultureInfoName=en-in&machineName=sg-pc-6h-acm-web-user-8697c4cd7c-gmgqx&trafficGroupId=5&trafficSubGroupId=122&aid=82361&useFullPageLogin=true&cttp=4&isRealUser=true&mode=production&browserFamily=Chrome&cdnDomain=agoda.net&checkIn=2025-08-12&checkOut=2025-08-13&rooms=1&adults=2&children=0&priceCur=INR&los=1&textToSearch=Darjeeling&travellerType=1&familyMode=off&ds=cgN73pCK5wrspJ7h&productType=-1"
    
    print("Agoda Enhanced Scraper - With Room Categories & Reviews")
    print("Enhanced Version with Proper URL Extraction")
    print("-" * 50)
    
    scraper = AgodaEnhancedScraper(search_url)
    scraper.run()

if __name__ == "__main__":
    main()