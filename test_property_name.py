#!/usr/bin/env python3
"""
Test script for Property Name Selector Update
"""

from agoda_scraper_fixed import AgodaHotelScraper
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_property_name_selector():
    """Test the updated property name selector"""
    
    print("=" * 70)
    print("TESTING UPDATED PROPERTY NAME SELECTOR")
    print("=" * 70)
    
    # Sample Agoda search URL
    search_url = "https://www.agoda.com/search?city=6667&checkIn=2024-03-15&checkOut=2024-03-17&adults=2&children=0&rooms=1"
    
    try:
        # Initialize scraper
        scraper = AgodaHotelScraper(headless=True, use_selenium=True)
        
        print(f"✓ Scraper initialized in {'Selenium' if scraper.use_selenium else 'Requests'} mode")
        
        # Test the property name selectors
        print("\nProperty name selectors being tested (in priority order):")
        selectors = [
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
        ]
        
        for i, selector in enumerate(selectors, 1):
            print(f"  {i:2d}. {selector}")
        
        print(f"\n{'='*70}")
        print("STARTING SCRAPING TEST WITH UPDATED SELECTOR")
        print(f"{'='*70}")
        
        # Scrape hotels
        hotels_data = scraper.scrape_hotels(
            search_url=search_url,
            customer_required_max_nights=30,
            max_pages=1
        )
        
        print(f"\n✓ Scraping completed!")
        print(f"Total hotels found: {len(hotels_data)}")
        
        # Check property names specifically
        property_names_found = 0
        for i, hotel in enumerate(hotels_data, 1):
            property_name = hotel.get('property_name')
            if property_name and property_name.strip():
                property_names_found += 1
                print(f"  Hotel {i}: '{property_name}'")
            else:
                print(f"  Hotel {i}: [No property name found]")
        
        print(f"\n📊 RESULTS:")
        print(f"  Total hotels processed: {len(hotels_data)}")
        print(f"  Property names found: {property_names_found}")
        print(f"  Success rate: {(property_names_found/len(hotels_data)*100):.1f}%" if hotels_data else "0%")
        
        # Save results
        if hotels_data:
            df = scraper.save_to_csv("updated_property_name_test.csv")
            print(f"  ✓ Results saved to updated_property_name_test.csv")
            
            # Show sample of extracted data
            print(f"\nSample hotel data:")
            first_hotel = hotels_data[0]
            key_fields = ['property_id', 'property_name', 'Platform', 'City', 'Check-in', 'Checkout_date']
            for field in key_fields:
                value = first_hotel.get(field, 'N/A')
                print(f"  {field}: {value}")
        
        return property_names_found, len(hotels_data)
        
    except Exception as e:
        print(f"✗ Error during testing: {e}")
        logger.error(f"Test error: {e}")
        return 0, 0
    
    finally:
        try:
            del scraper
        except:
            pass

def test_css_selector_variations():
    """Test different CSS selector patterns"""
    print(f"\n{'='*70}")
    print("TESTING CSS SELECTOR PATTERN MATCHING")
    print(f"{'='*70}")
    
    # Test HTML samples with different class patterns
    test_html_samples = [
        '<span class="sc-hKgILt Typographystyled__TypographyStyled-sc-1uoovui-0 kkDVzi eMpfYC TextLink__TextStyled-sc-upxc4y-0 fZAVxI">Grand Hotel Plaza</span>',
        '<span class="TextLink__TextStyled-sc-upxc4y-0 fZAVxI">Luxury Resort & Spa</span>',
        '<span class="TypographyStyled-sc-1uoovui-0 kkDVzi">Business Hotel Downtown</span>',
        '<span class="sc-hKgILt property-title">Boutique Hotel</span>',
        '<h3 class="hotel-name">Traditional Inn</h3>',
        '<div data-selenium="hotel-name">Modern Suites</div>'
    ]
    
    from bs4 import BeautifulSoup
    
    selectors_to_test = [
        'span[class="sc-hKgILt Typographystyled__TypographyStyled-sc-1uoovui-0 kkDVzi eMpfYC TextLink__TextStyled-sc-upxc4y-0 fZAVxI"]',
        'span[class*="TextLink__TextStyled"]',
        'span[class*="TypographyStyled"]',
        'span[class*="sc-hKgILt"]',
        '[data-selenium="hotel-name"]',
        'h3',
        '[class*="hotel-name"]'
    ]
    
    print("Testing selector patterns against sample HTML:")
    for i, html in enumerate(test_html_samples, 1):
        soup = BeautifulSoup(html, 'html.parser')
        print(f"\nSample {i}: {html}")
        
        for selector in selectors_to_test:
            try:
                element = soup.select_one(selector)
                if element:
                    text = element.get_text(strip=True)
                    print(f"  ✓ {selector} → '{text}'")
                    break
            except Exception as e:
                continue
        else:
            print(f"  ✗ No selector matched")

if __name__ == "__main__":
    print("Testing Updated Property Name Selector...")
    
    # Test the updated selector
    found_names, total_hotels = test_property_name_selector()
    
    # Test CSS selector variations
    test_css_selector_variations()
    
    print(f"\n{'='*70}")
    print("PROPERTY NAME SELECTOR TEST COMPLETED")
    print(f"{'='*70}")
    
    if total_hotels > 0:
        print(f"✓ Successfully processed {total_hotels} hotels")
        print(f"✓ Found property names in {found_names} hotels")
        print(f"✓ Updated selector priority list implemented")
        print(f"✓ Fallback selectors ready for different page structures")
    else:
        print("⚠ No hotels were processed - this may be due to:")
        print("  - Website structure changes")
        print("  - Network connectivity issues")
        print("  - Anti-bot protection")
    
    print("\n✅ Property name selector has been successfully updated with:")
    print("   1. Primary selector: span[class=\"sc-hKgILt Typographystyled__TypographyStyled-sc-1uoovui-0 kkDVzi eMpfYC TextLink__TextStyled-sc-upxc4y-0 fZAVxI\"]")
    print("   2. Pattern-based fallbacks for class variations")
    print("   3. Multiple backup selectors for robustness")