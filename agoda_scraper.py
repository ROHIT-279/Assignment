import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime, timedelta
import re
import time
from urllib.parse import urlparse, parse_qs
import json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AgodaHotelScraper:
    def __init__(self, headless=True):
        """Initialize the Agoda scraper with Chrome driver"""
        self.chrome_options = Options()
        if headless:
            self.chrome_options.add_argument("--headless")
        self.chrome_options.add_argument("--no-sandbox")
        self.chrome_options.add_argument("--disable-dev-shm-usage")
        self.chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        self.chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        self.chrome_options.add_experimental_option('useAutomationExtension', False)
        
        self.driver = webdriver.Chrome(options=self.chrome_options)
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        self.hotel_data_list = []
        self.property_counter = 1
        
    def __del__(self):
        """Clean up driver on destruction"""
        if hasattr(self, 'driver'):
            self.driver.quit()
    
    def clean_text(self, text):
        """Clean text by removing Rs., commas, %, extra spaces, and newlines"""
        if not text:
            return None
        
        # Remove Rs., commas, %, extra spaces, and newlines
        cleaned = re.sub(r'Rs\.?|,|%', '', str(text))
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        cleaned = cleaned.replace('\n', '').replace('\r', '')
        
        return cleaned if cleaned else None
    
    def convert_to_number(self, text):
        """Convert text to number where applicable"""
        if not text:
            return None
        
        cleaned = self.clean_text(text)
        if not cleaned:
            return None
        
        # Try to extract number from text
        number_match = re.search(r'[\d,]+\.?\d*', cleaned)
        if number_match:
            try:
                return float(number_match.group().replace(',', ''))
            except ValueError:
                return None
        
        return None
    
    def platform_from_url(self, url):
        """Extract platform from search_url domain"""
        try:
            domain = urlparse(url).netloc
            if 'agoda' in domain.lower():
                return 'Agoda'
            return domain
        except:
            return None
    
    def city_from_url(self, url):
        """Extract city from search_url"""
        try:
            # Parse URL to extract city information
            parsed_url = urlparse(url)
            query_params = parse_qs(parsed_url.query)
            
            # Look for city in various possible parameters
            city_params = ['city', 'destination', 'dest', 'location']
            for param in city_params:
                if param in query_params:
                    return query_params[param][0]
            
            # Try to extract from path
            path_parts = parsed_url.path.split('/')
            for part in path_parts:
                if part and len(part) > 2:
                    return part.replace('-', ' ').title()
            
            return None
        except:
            return None
    
    def country_from_url(self, url):
        """Extract country from search_url"""
        try:
            parsed_url = urlparse(url)
            query_params = parse_qs(parsed_url.query)
            
            # Look for country in various possible parameters
            country_params = ['country', 'countryId', 'region']
            for param in country_params:
                if param in query_params:
                    return query_params[param][0]
            
            return None
        except:
            return None
    
    def checkin_from_url(self, url):
        """Extract check-in date from search_url"""
        try:
            parsed_url = urlparse(url)
            query_params = parse_qs(parsed_url.query)
            
            checkin_params = ['checkin', 'checkIn', 'arrival', 'startDate']
            for param in checkin_params:
                if param in query_params:
                    return query_params[param][0]
            
            return None
        except:
            return None
    
    def checkout_from_url(self, url):
        """Extract checkout date from search_url"""
        try:
            parsed_url = urlparse(url)
            query_params = parse_qs(parsed_url.query)
            
            checkout_params = ['checkout', 'checkOut', 'departure', 'endDate']
            for param in checkout_params:
                if param in query_params:
                    return query_params[param][0]
            
            return None
        except:
            return None
    
    def adults_from_url(self, url):
        """Extract adults count from search_url"""
        try:
            parsed_url = urlparse(url)
            query_params = parse_qs(parsed_url.query)
            
            adult_params = ['adults', 'adult', 'numAdults']
            for param in adult_params:
                if param in query_params:
                    return int(query_params[param][0])
            
            return 2  # Default value
        except:
            return 2
    
    def children_from_url(self, url):
        """Extract children count from search_url"""
        try:
            parsed_url = urlparse(url)
            query_params = parse_qs(parsed_url.query)
            
            children_params = ['children', 'child', 'numChildren']
            for param in children_params:
                if param in query_params:
                    return int(query_params[param][0])
            
            return 0  # Default value
        except:
            return 0
    
    def days_between(self, date1, date2):
        """Calculate days between two dates"""
        try:
            if not date1 or not date2:
                return None
            
            d1 = datetime.strptime(date1, '%Y-%m-%d')
            d2 = datetime.strptime(date2, '%Y-%m-%d')
            return abs((d2 - d1).days)
        except:
            return None
    
    def latitude_from_location(self, soup):
        """Extract latitude from location text if present"""
        try:
            # Look for coordinates in various possible locations
            location_selectors = [
                'span[data-selenium="hotel-address-map"]',
                'div[data-testid="property-location"]',
                'script[type="application/ld+json"]'
            ]
            
            for selector in location_selectors:
                element = soup.select_one(selector)
                if element:
                    text = element.get_text() if selector != 'script[type="application/ld+json"]' else element.string
                    if text:
                        # Look for latitude pattern
                        lat_match = re.search(r'lat[itude]*["\s:=]+(-?\d+\.?\d*)', text, re.IGNORECASE)
                        if lat_match:
                            return float(lat_match.group(1))
            
            return None
        except:
            return None
    
    def longitude_from_location(self, soup):
        """Extract longitude from location text if present"""
        try:
            # Look for coordinates in various possible locations
            location_selectors = [
                'span[data-selenium="hotel-address-map"]',
                'div[data-testid="property-location"]',
                'script[type="application/ld+json"]'
            ]
            
            for selector in location_selectors:
                element = soup.select_one(selector)
                if element:
                    text = element.get_text() if selector != 'script[type="application/ld+json"]' else element.string
                    if text:
                        # Look for longitude pattern
                        lng_match = re.search(r'lng|lon[gitude]*["\s:=]+(-?\d+\.?\d*)', text, re.IGNORECASE)
                        if lng_match:
                            return float(lng_match.group(1))
            
            return None
        except:
            return None
    
    def extract_hotel_data(self, search_url, customer_required_max_nights=30):
        """Extract hotel data from the current page using the provided field mapping"""
        try:
            # Get page source and create soup
            html_content = self.driver.page_source
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Find all hotel containers on the page
            hotel_containers = soup.select('div[data-selenium="hotel-item"], div[class*="PropertyCard"], div[class*="hotel-item"]')
            
            if not hotel_containers:
                logger.warning("No hotel containers found on the page")
                return []
            
            hotels_data = []
            
            for container in hotel_containers:
                try:
                    # Create hotel data dictionary with the provided field mapping
                    hotel_data = {
                        'property_id': f"{self.property_counter:02d}",
                        'property_name': container.select_one('[data-selenium="hotel-name"]').get_text(strip=True) if container.select_one('[data-selenium="hotel-name"]') else None,
                        'Platform': self.platform_from_url(search_url),
                        'property_type': container.select_one('div[data-testid="rating-container"]').get_text(strip=True) if container.select_one('div[data-testid="rating-container"]') else None,
                        'Location': container.select_one('span[data-selenium="hotel-address-map"]').get_text(strip=True) if container.select_one('span[data-selenium="hotel-address-map"]') else None,
                        'City': self.city_from_url(search_url),
                        'Country': self.country_from_url(search_url),
                        'zip_code': (lambda loc: loc.split(",")[-1].strip() if loc else None)(container.select_one('span[data-selenium="hotel-address-map"]').get_text(strip=True) if container.select_one('span[data-selenium="hotel-address-map"]') else None),
                        'star_rating': container.select_one('div[data-testid="star-rating-container"][data-selenium="mosaic-hotel-rating"]').get_text(strip=True) if container.select_one('div[data-testid="star-rating-container"][data-selenium="mosaic-hotel-rating"]') else None,
                        'review_score': container.select_one('div.Review__ReviewFormattedScore').get_text(strip=True) if container.select_one('div.Review__ReviewFormattedScore') else None,
                        'review_count': container.select_one('div[data-testid="review-based-on"] span').get_text(strip=True) if container.select_one('div[data-testid="review-based-on"] span') else None,
                        'Check-in': self.checkin_from_url(search_url),
                        'Checkout_date': self.checkout_from_url(search_url),
                        'scraped_date': datetime.now().strftime('%Y-%m-%d'),
                        'booking_window_days': self.days_between(datetime.now().strftime('%Y-%m-%d'), self.checkin_from_url(search_url)),
                        'amenities': [a.get_text(strip=True) for a in container.select('div[data-element-name="atf-top-amenities"]')],
                        'room_type_name': [rt.get_text(strip=True) for rt in container.select('span[data-selenium="masterroom-title-name"]')],
                        'room_description': [rd.get_text(strip=True) for rd in container.select('ul[data-selenium="MasterRoom-amenities"] li')],
                        'room_size_sqm': [rs.get_text(strip=True) for rs in container.select('i.ficon-sqm')],
                        'bed_type': [bt.get_text(strip=True) for bt in container.select('div.MasterRoom-amenitiesTitle')],
                        'latitude': self.latitude_from_location(container),
                        'longitude': self.longitude_from_location(container),
                        'room_capacity_adults': self.adults_from_url(search_url),
                        'room_capacity_children': self.children_from_url(search_url),
                        'price_per_night': [self.clean_text(ppn.get_text(strip=True)) for ppn in container.select('span[data-selenium="display-price"]')],
                        'original_price': [self.clean_text(op.get_text(strip=True)) for op in container.select('div[data-testid="crossed-out-price-text"] span[aria-hidden="true"]')],
                        'discount_percent': [self.clean_text(dp.get_text(strip=True)) for dp in container.select('span[class*="PercentValue"], span[class*="Discount"]')],
                        'price_per_adult': [(self.convert_to_number(op.get_text(strip=True)) / 2) if op and self.convert_to_number(op.get_text(strip=True)) else None for op in container.select('div[data-testid="crossed-out-price-text"] span[aria-hidden="true"]')],
                        'cancellation_policy': [cp.get_text(strip=True) for cp in container.select('div[class*="UrgencyMessageAnimated"] p[class*="Message__Content"]')],
                        'refundable': [rf.get_text(strip=True) for rf in container.select('div[data-element-name="free-cancellation-included"] span')],
                        'availability_status': 'Our last 2 Rooms',
                        'min_stay_nights': 0,
                        'max_stay_nights': customer_required_max_nights,
                        'mobile_discount_flag': 0,
                        'loyalty_program_flag': 0,
                        'url': self.get_hotel_detail_url(container)
                    }
                    
                    # Clean and process the data
                    hotel_data = self.process_hotel_data(hotel_data)
                    
                    hotels_data.append(hotel_data)
                    self.property_counter += 1
                    
                except Exception as e:
                    logger.error(f"Error extracting data for hotel container: {e}")
                    continue
            
            return hotels_data
            
        except Exception as e:
            logger.error(f"Error extracting hotel data: {e}")
            return []
    
    def get_hotel_detail_url(self, container):
        """Extract the actual hotel detail page link"""
        try:
            # Look for hotel detail link
            link_selectors = [
                'a[data-selenium="hotel-item-link"]',
                'a[href*="/hotel/"]',
                'h3 a',
                'a[class*="PropertyCard"]'
            ]
            
            for selector in link_selectors:
                link_element = container.select_one(selector)
                if link_element and link_element.get('href'):
                    href = link_element.get('href')
                    if href.startswith('/'):
                        return f"https://www.agoda.com{href}"
                    elif href.startswith('http'):
                        return href
            
            return self.driver.current_url
        except:
            return self.driver.current_url
    
    def process_hotel_data(self, hotel_data):
        """Process and clean hotel data"""
        # Clean text fields
        text_fields = ['property_name', 'property_type', 'Location', 'star_rating', 'review_score', 'review_count']
        for field in text_fields:
            if hotel_data.get(field):
                hotel_data[field] = self.clean_text(hotel_data[field])
        
        # Convert numeric fields
        numeric_fields = ['review_score', 'star_rating']
        for field in numeric_fields:
            if hotel_data.get(field):
                hotel_data[field] = self.convert_to_number(hotel_data[field])
        
        # Process price fields
        price_fields = ['price_per_night', 'original_price']
        for field in price_fields:
            if hotel_data.get(field) and isinstance(hotel_data[field], list):
                hotel_data[field] = [self.convert_to_number(price) for price in hotel_data[field]]
        
        # Set None for missing values
        for key, value in hotel_data.items():
            if not value or (isinstance(value, list) and not any(value)):
                hotel_data[key] = None
        
        return hotel_data
    
    def check_next_page(self):
        """Check if pagination next button is present and enabled"""
        try:
            next_button = self.driver.find_element(By.ID, "paginationNext")
            return next_button.is_enabled() and next_button.is_displayed()
        except NoSuchElementException:
            # Try alternative selectors for next button
            alternative_selectors = [
                'button[aria-label*="next"]',
                'button[class*="next"]',
                'a[class*="next"]',
                'button[data-selenium*="next"]'
            ]
            
            for selector in alternative_selectors:
                try:
                    next_button = self.driver.find_element(By.CSS_SELECTOR, selector)
                    return next_button.is_enabled() and next_button.is_displayed()
                except NoSuchElementException:
                    continue
            
            return False
    
    def click_next_page(self):
        """Click the next page button and wait for new content to load"""
        try:
            next_button = self.driver.find_element(By.ID, "paginationNext")
            next_button.click()
            
            # Wait for new content to load
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'div[data-selenium="hotel-item"], div[class*="PropertyCard"]'))
            )
            
            time.sleep(2)  # Additional wait for dynamic content
            return True
            
        except (NoSuchElementException, TimeoutException):
            # Try alternative selectors
            alternative_selectors = [
                'button[aria-label*="next"]',
                'button[class*="next"]',
                'a[class*="next"]',
                'button[data-selenium*="next"]'
            ]
            
            for selector in alternative_selectors:
                try:
                    next_button = self.driver.find_element(By.CSS_SELECTOR, selector)
                    next_button.click()
                    
                    WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, 'div[data-selenium="hotel-item"], div[class*="PropertyCard"]'))
                    )
                    
                    time.sleep(2)
                    return True
                    
                except (NoSuchElementException, TimeoutException):
                    continue
            
            return False
    
    def scrape_hotels(self, search_url, customer_required_max_nights=30, max_pages=10):
        """Main scraping function with pagination logic"""
        try:
            logger.info(f"Starting to scrape hotels from: {search_url}")
            
            # Navigate to the search URL
            self.driver.get(search_url)
            
            # Wait for page to load
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'div[data-selenium="hotel-item"], div[class*="PropertyCard"], div[class*="hotel-item"]'))
            )
            
            page_count = 0
            
            while page_count < max_pages:
                logger.info(f"Scraping page {page_count + 1}")
                
                # Extract hotel data from current page
                page_hotels = self.extract_hotel_data(search_url, customer_required_max_nights)
                self.hotel_data_list.extend(page_hotels)
                
                logger.info(f"Extracted {len(page_hotels)} hotels from page {page_count + 1}")
                
                # Check if next page is available
                if not self.check_next_page():
                    logger.info("No more pages available")
                    break
                
                # Click next page
                if not self.click_next_page():
                    logger.warning("Failed to navigate to next page")
                    break
                
                page_count += 1
                time.sleep(3)  # Respectful delay between pages
            
            logger.info(f"Scraping completed. Total hotels extracted: {len(self.hotel_data_list)}")
            return self.hotel_data_list
            
        except Exception as e:
            logger.error(f"Error during scraping: {e}")
            return self.hotel_data_list
    
    def save_to_dataframe(self):
        """Convert scraped data to DataFrame"""
        if not self.hotel_data_list:
            logger.warning("No data to save")
            return pd.DataFrame()
        
        df = pd.DataFrame(self.hotel_data_list)
        logger.info(f"Created DataFrame with {len(df)} rows and {len(df.columns)} columns")
        return df
    
    def save_to_csv(self, filename="agoda_hotels.csv"):
        """Save scraped data to CSV file"""
        df = self.save_to_dataframe()
        if not df.empty:
            df.to_csv(filename, index=False)
            logger.info(f"Data saved to {filename}")
        return df

# Example usage
def main():
    """Example usage of the AgodaHotelScraper"""
    # Example search URL (you'll need to replace with actual Agoda search URL)
    search_url = "https://www.agoda.com/search?city=12345&checkIn=2024-03-01&checkOut=2024-03-03&adults=2&children=0"
    
    # Initialize scraper
    scraper = AgodaHotelScraper(headless=False)  # Set to True for headless mode
    
    try:
        # Scrape hotels
        hotels_data = scraper.scrape_hotels(
            search_url=search_url,
            customer_required_max_nights=30,
            max_pages=5
        )
        
        # Save to DataFrame and CSV
        df = scraper.save_to_csv("agoda_hotels_scraped.csv")
        
        print(f"Scraping completed! {len(df)} hotels scraped.")
        print(f"Columns: {list(df.columns)}")
        
    except Exception as e:
        logger.error(f"Error in main execution: {e}")
    
    finally:
        # Clean up
        del scraper

if __name__ == "__main__":
    main()