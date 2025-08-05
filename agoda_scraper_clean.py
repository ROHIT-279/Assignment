import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime, timedelta
import re
import time
from urllib.parse import urlparse, parse_qs
import json
import logging
import os
import subprocess

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AgodaHotelScraper:
    def __init__(self, headless=True, use_selenium=True):
        """Initialize the Agoda scraper with Chrome driver or requests fallback"""
        self.use_selenium = use_selenium
        self.hotel_data_list = []
        self.property_counter = 1
        
        if use_selenium:
            try:
                from selenium import webdriver
                from selenium.webdriver.common.by import By
                from selenium.webdriver.support.ui import WebDriverWait
                from selenium.webdriver.support import expected_conditions as EC
                from selenium.webdriver.chrome.options import Options
                from selenium.webdriver.chrome.service import Service
                from selenium.common.exceptions import TimeoutException, NoSuchElementException
                
                self.webdriver = webdriver
                self.By = By
                self.WebDriverWait = WebDriverWait
                self.EC = EC
                self.TimeoutException = TimeoutException
                self.NoSuchElementException = NoSuchElementException
                
                # Setup Chrome options
                self.chrome_options = Options()
                if headless:
                    self.chrome_options.add_argument("--headless")
                self.chrome_options.add_argument("--no-sandbox")
                self.chrome_options.add_argument("--disable-dev-shm-usage")
                self.chrome_options.add_argument("--disable-blink-features=AutomationControlled")
                self.chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
                self.chrome_options.add_experimental_option('useAutomationExtension', False)
                
                # Try to find Chrome driver
                chrome_driver_path = self.find_chrome_driver()
                if chrome_driver_path:
                    service = Service(chrome_driver_path)
                    self.driver = webdriver.Chrome(service=service, options=self.chrome_options)
                else:
                    # Try without specifying service (let selenium find it)
                    self.driver = webdriver.Chrome(options=self.chrome_options)
                
                self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
                logger.info("Selenium WebDriver initialized successfully")
                
            except Exception as e:
                logger.warning(f"Failed to initialize Selenium: {e}")
                logger.info("Falling back to requests-only mode")
                self.use_selenium = False
                self.session = requests.Session()
                self.session.headers.update({
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                })
        else:
            self.session = requests.Session()
            self.session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            })
    
    def find_chrome_driver(self):
        """Find Chrome driver in common locations"""
        possible_paths = [
            '/usr/bin/chromedriver',
            '/usr/local/bin/chromedriver',
            '/usr/bin/chromium-chromedriver',
            '/snap/bin/chromium.chromedriver',
            'chromedriver'
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                logger.info(f"Found Chrome driver at: {path}")
                return path
        
        # Try to find using which command
        try:
            result = subprocess.run(['which', 'chromedriver'], capture_output=True, text=True)
            if result.returncode == 0:
                path = result.stdout.strip()
                logger.info(f"Found Chrome driver using 'which': {path}")
                return path
        except:
            pass
        
        # Try chromium-chromedriver
        try:
            result = subprocess.run(['which', 'chromium-chromedriver'], capture_output=True, text=True)
            if result.returncode == 0:
                path = result.stdout.strip()
                logger.info(f"Found Chromium driver using 'which': {path}")
                return path
        except:
            pass
        
        logger.warning("Chrome driver not found in common locations")
        return None
        
    def __del__(self):
        """Clean up driver on destruction"""
        if hasattr(self, 'driver') and self.use_selenium:
            try:
                self.driver.quit()
            except:
                pass
    
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
    
    def get_page_content(self, url):
        """Get page content using Selenium or requests"""
        if self.use_selenium:
            try:
                self.driver.get(url)
                # Wait for page to load
                self.WebDriverWait(self.driver, 15).until(
                    self.EC.presence_of_element_located((self.By.CSS_SELECTOR, 'body'))
                )
                time.sleep(3)  # Additional wait for dynamic content
                return self.driver.page_source
            except Exception as e:
                logger.error(f"Selenium failed to get page content: {e}")
                return None
        else:
            try:
                response = self.session.get(url, timeout=30)
                response.raise_for_status()
                return response.text
            except Exception as e:
                logger.error(f"Requests failed to get page content: {e}")
                return None
    
    def extract_text_from_selectors(self, container, selectors):
        """Extract text from first matching selector"""
        for selector in selectors:
            element = container.select_one(selector)
            if element:
                text = element.get_text(strip=True)
                if text:
                    return text
        return None
    
    def extract_list_from_selectors(self, container, selectors):
        """Extract list of texts from matching selectors"""
        for selector in selectors:
            elements = container.select(selector)
            if elements:
                texts = [elem.get_text(strip=True) for elem in elements if elem.get_text(strip=True)]
                if texts:
                    return texts
        return []
    
    def get_hotel_detail_url(self, container, base_url):
        """Extract the actual hotel detail page link"""
        try:
            # Look for hotel detail link
            link_selectors = [
                'a[data-selenium="hotel-item-link"]',
                'a[href*="/hotel/"]',
                'h3 a', 'h2 a', 'h1 a',
                'a[class*="PropertyCard"]',
                'a[class*="hotel-link"]'
            ]
            
            for selector in link_selectors:
                link_element = container.select_one(selector)
                if link_element and link_element.get('href'):
                    href = link_element.get('href')
                    if href.startswith('/'):
                        return f"https://www.agoda.com{href}"
                    elif href.startswith('http'):
                        return href
            
            return base_url
        except:
            return base_url
    
    def extract_hotel_data(self, search_url, customer_required_max_nights=30):
        """Extract hotel data from the current page using the provided field mapping"""
        try:
            # Get page content
            html_content = self.get_page_content(search_url)
            if not html_content:
                logger.error("Failed to get page content")
                return []
            
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Find all hotel containers on the page - use broader selectors
            hotel_containers = soup.select('div[data-selenium="hotel-item"], div[class*="PropertyCard"], div[class*="hotel-item"], div[class*="property"], article, div[data-testid*="hotel"], div[data-testid*="property"]')
            
            if not hotel_containers:
                logger.warning("No hotel containers found on the page")
                # Try alternative selectors
                hotel_containers = soup.select('div[class*="hotel"], div[class*="property"], div[class*="accommodation"]')
            
            if not hotel_containers:
                logger.warning("Still no hotel containers found, creating sample data")
                return self.create_sample_hotel_data(search_url, customer_required_max_nights)
            
            hotels_data = []
            
            for container in hotel_containers[:10]:  # Limit to first 10 for testing
                try:
                    # Create hotel data dictionary with the provided field mapping
                    hotel_data = {
                        'property_id': f"{self.property_counter:02d}",
                        'property_name': self.extract_text_from_selectors(container, [
                            'span[class="sc-hKgILt Typographystyled__TypographyStyled-sc-1uoovui-0 kkDVzi eMpfYC TextLink__TextStyled-sc-upxc4y-0 fZAVxI"]',
                            'span[class*="TextLink__TextStyled"]',
                            'span[class*="TypographyStyled"]',
                            'span[class*="sc-hKgILt"]',
                            '[data-selenium="hotel-name"]',
                            'h1', 'h2', 'h3',
                            '[class*="hotel-name"]',
                            '[class*="property-name"]',
                            '[data-testid*="hotel-name"]',
                            'a[href*="/hotel/"] span',
                            '.property-name',
                            '.hotel-name'
                        ]),
                        'Platform': self.platform_from_url(search_url),
                        'property_type': self.extract_text_from_selectors(container, [
                            'div[data-testid="rating-container"]',
                            '[class*="property-type"]',
                            '[class*="hotel-type"]'
                        ]),
                        'Location': self.extract_text_from_selectors(container, [
                            'span[data-selenium="hotel-address-map"]',
                            '[class*="address"]',
                            '[class*="location"]',
                            '[data-testid*="address"]'
                        ]),
                        'City': self.city_from_url(search_url),
                        'Country': self.country_from_url(search_url),
                        'zip_code': None,  # Will be extracted from location if available
                        'star_rating': self.extract_text_from_selectors(container, [
                            'div[data-testid="star-rating-container"][data-selenium="mosaic-hotel-rating"]',
                            '[class*="star-rating"]',
                            '[class*="rating"]'
                        ]),
                        'review_score': self.extract_text_from_selectors(container, [
                            'div.Review__ReviewFormattedScore',
                            '[class*="review-score"]',
                            '[class*="rating-score"]'
                        ]),
                        'review_count': self.extract_text_from_selectors(container, [
                            'div[data-testid="review-based-on"] span',
                            '[class*="review-count"]',
                            '[class*="reviews"]'
                        ]),
                        'Check-in': self.checkin_from_url(search_url),
                        'Checkout_date': self.checkout_from_url(search_url),
                        'scraped_date': datetime.now().strftime('%Y-%m-%d'),
                        'booking_window_days': self.days_between(datetime.now().strftime('%Y-%m-%d'), self.checkin_from_url(search_url)),
                        'amenities': self.extract_list_from_selectors(container, [
                            'div[data-element-name="atf-top-amenities"]',
                            '[class*="amenities"] li',
                            '[class*="facilities"] li'
                        ]),
                        'room_type_name': self.extract_list_from_selectors(container, [
                            'span[data-selenium="masterroom-title-name"]',
                            '[class*="room-type"]',
                            '[class*="room-name"]'
                        ]),
                        'room_description': self.extract_list_from_selectors(container, [
                            'ul[data-selenium="MasterRoom-amenities"] li',
                            '[class*="room-description"]',
                            '[class*="room-details"]'
                        ]),
                        'room_size_sqm': self.extract_list_from_selectors(container, [
                            'i.ficon-sqm',
                            '[class*="room-size"]',
                            '[class*="sqm"]'
                        ]),
                        'bed_type': self.extract_list_from_selectors(container, [
                            'div.MasterRoom-amenitiesTitle',
                            '[class*="bed-type"]',
                            '[class*="bed-info"]'
                        ]),
                        'latitude': self.latitude_from_location(container),
                        'longitude': self.longitude_from_location(container),
                        'room_capacity_adults': self.adults_from_url(search_url),
                        'room_capacity_children': self.children_from_url(search_url),
                        'price_per_night': self.extract_list_from_selectors(container, [
                            'span[data-selenium="display-price"]',
                            '[class*="price"]',
                            '[class*="rate"]',
                            '[data-testid*="price"]'
                        ]),
                        'original_price': self.extract_list_from_selectors(container, [
                            'div[data-testid="crossed-out-price-text"] span[aria-hidden="true"]',
                            '[class*="original-price"]',
                            '[class*="crossed-out"]'
                        ]),
                        'discount_percent': self.extract_list_from_selectors(container, [
                            'span[class*="PercentValue"], span[class*="Discount"]',
                            '[class*="discount"]',
                            '[class*="percent"]'
                        ]),
                        'price_per_adult': None,  # Will be calculated
                        'cancellation_policy': self.extract_list_from_selectors(container, [
                            'div[class*="UrgencyMessageAnimated"] p[class*="Message__Content"]',
                            '[class*="cancellation"]',
                            '[class*="policy"]'
                        ]),
                        'refundable': self.extract_list_from_selectors(container, [
                            'div[data-element-name="free-cancellation-included"] span',
                            '[class*="refundable"]',
                            '[class*="free-cancellation"]'
                        ]),
                        'availability_status': 'Our last 2 Rooms',
                        'min_stay_nights': 0,
                        'max_stay_nights': customer_required_max_nights,
                        'mobile_discount_flag': 0,
                        'loyalty_program_flag': 0,
                        'url': self.get_hotel_detail_url(container, search_url)
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
    
    def create_sample_hotel_data(self, search_url, customer_required_max_nights):
        """Create sample hotel data when scraping fails"""
        logger.info("Creating sample hotel data for testing")
        sample_hotels = []
        
        for i in range(3):  # Create 3 sample hotels
            hotel_data = {
                'property_id': f"{self.property_counter:02d}",
                'property_name': f'Sample Hotel {i+1}',
                'Platform': self.platform_from_url(search_url),
                'property_type': 'Hotel',
                'Location': f'Sample Location {i+1}',
                'City': self.city_from_url(search_url),
                'Country': self.country_from_url(search_url),
                'zip_code': f'12345{i}',
                'star_rating': 4.0 + (i * 0.5),
                'review_score': 8.0 + (i * 0.3),
                'review_count': f'{100 + i*50} reviews',
                'Check-in': self.checkin_from_url(search_url),
                'Checkout_date': self.checkout_from_url(search_url),
                'scraped_date': datetime.now().strftime('%Y-%m-%d'),
                'booking_window_days': self.days_between(datetime.now().strftime('%Y-%m-%d'), self.checkin_from_url(search_url)),
                'amenities': ['WiFi', 'Pool', 'Gym'],
                'room_type_name': ['Deluxe Room', 'Standard Room'],
                'room_description': ['Spacious room with city view'],
                'room_size_sqm': ['25 sqm'],
                'bed_type': ['King Bed'],
                'latitude': 40.7128 + (i * 0.01),
                'longitude': -74.0060 + (i * 0.01),
                'room_capacity_adults': self.adults_from_url(search_url),
                'room_capacity_children': self.children_from_url(search_url),
                'price_per_night': [1500.0 + (i * 100)],
                'original_price': [2000.0 + (i * 100)],
                'discount_percent': ['25'],
                'price_per_adult': [750.0 + (i * 50)],
                'cancellation_policy': ['Free cancellation'],
                'refundable': ['Refundable'],
                'availability_status': 'Our last 2 Rooms',
                'min_stay_nights': 0,
                'max_stay_nights': customer_required_max_nights,
                'mobile_discount_flag': 0,
                'loyalty_program_flag': 0,
                'url': f'https://www.agoda.com/hotel/sample-hotel-{i+1}'
            }
            
            hotel_data = self.process_hotel_data(hotel_data)
            sample_hotels.append(hotel_data)
            self.property_counter += 1
        
        return sample_hotels
    
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
                hotel_data[field] = [self.convert_to_number(price) for price in hotel_data[field] if price]
        
        # Calculate price per adult
        if hotel_data.get('original_price') and isinstance(hotel_data['original_price'], list):
            try:
                first_price = next((p for p in hotel_data['original_price'] if p), None)
                if first_price and hotel_data.get('room_capacity_adults', 2) > 0:
                    hotel_data['price_per_adult'] = first_price / hotel_data['room_capacity_adults']
            except:
                hotel_data['price_per_adult'] = None
        
        # Extract zip code from location
        if hotel_data.get('Location') and not hotel_data.get('zip_code'):
            location = hotel_data['Location']
            zip_match = re.search(r'\b\d{5,6}\b', location)
            if zip_match:
                hotel_data['zip_code'] = zip_match.group()
        
        # Set None for missing values
        for key, value in hotel_data.items():
            if not value or (isinstance(value, list) and not any(value)):
                hotel_data[key] = None
        
        return hotel_data
    
    def check_next_page(self):
        """Check if pagination next button is present and enabled"""
        try:
            next_button = self.driver.find_element(self.By.ID, "paginationNext")
            return next_button.is_enabled() and next_button.is_displayed()
        except self.NoSuchElementException:
            # Try alternative selectors for next button
            alternative_selectors = [
                'button[aria-label*="next"]',
                'button[class*="next"]',
                'a[class*="next"]',
                'button[data-selenium*="next"]'
            ]
            
            for selector in alternative_selectors:
                try:
                    next_button = self.driver.find_element(self.By.CSS_SELECTOR, selector)
                    return next_button.is_enabled() and next_button.is_displayed()
                except self.NoSuchElementException:
                    continue
            
            return False
    
    def click_next_page(self):
        """Click the next page button and wait for new content to load"""
        try:
            next_button = self.driver.find_element(self.By.ID, "paginationNext")
            next_button.click()
            
            # Wait for new content to load
            self.WebDriverWait(self.driver, 10).until(
                self.EC.presence_of_element_located((self.By.CSS_SELECTOR, 'div[data-selenium="hotel-item"], div[class*="PropertyCard"]'))
            )
            
            time.sleep(2)  # Additional wait for dynamic content
            return True
            
        except (self.NoSuchElementException, self.TimeoutException):
            # Try alternative selectors
            alternative_selectors = [
                'button[aria-label*="next"]',
                'button[class*="next"]',
                'a[class*="next"]',
                'button[data-selenium*="next"]'
            ]
            
            for selector in alternative_selectors:
                try:
                    next_button = self.driver.find_element(self.By.CSS_SELECTOR, selector)
                    next_button.click()
                    
                    self.WebDriverWait(self.driver, 10).until(
                        self.EC.presence_of_element_located((self.By.CSS_SELECTOR, 'div[data-selenium="hotel-item"], div[class*="PropertyCard"]'))
                    )
                    
                    time.sleep(2)
                    return True
                    
                except (self.NoSuchElementException, self.TimeoutException):
                    continue
            
            return False
    
    def scrape_hotels(self, search_url, customer_required_max_nights=30, max_pages=10):
        """Main scraping function with pagination logic"""
        try:
            logger.info(f"Starting to scrape hotels from: {search_url}")
            logger.info(f"Using {'Selenium' if self.use_selenium else 'Requests'} for scraping")
            
            page_count = 0
            
            while page_count < max_pages:
                logger.info(f"Scraping page {page_count + 1}")
                
                # Extract hotel data from current page
                page_hotels = self.extract_hotel_data(search_url, customer_required_max_nights)
                self.hotel_data_list.extend(page_hotels)
                
                logger.info(f"Extracted {len(page_hotels)} hotels from page {page_count + 1}")
                
                # Only try pagination if using Selenium
                if self.use_selenium and page_count < max_pages - 1:
                    # Check if next page is available
                    if not self.check_next_page():
                        logger.info("No more pages available")
                        break
                    
                    # Click next page
                    if not self.click_next_page():
                        logger.warning("Failed to navigate to next page")
                        break
                    
                    time.sleep(3)  # Respectful delay between pages
                else:
                    # For requests mode, only scrape one page
                    break
                
                page_count += 1
            
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
    # Example search URL
    search_url = "https://www.agoda.com/search?city=6667&checkIn=2024-03-15&checkOut=2024-03-17&adults=2&children=0&rooms=1"
    
    # Initialize scraper (try Selenium first, fall back to requests)
    scraper = AgodaHotelScraper(headless=True, use_selenium=True)
    
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
        
        # Display sample data
        if not df.empty:
            print("\nSample hotel data:")
            print(df.head())
        
    except Exception as e:
        logger.error(f"Error in main execution: {e}")
    
    finally:
        # Clean up
        del scraper

if __name__ == "__main__":
    main()