#!/usr/bin/env python3
"""
Test script for Agoda Hotel Scraper
"""

import sys
import os
from agoda_scraper import AgodaHotelScraper
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_agoda_scraper():
    """Test the Agoda scraper with a sample search URL"""
    
    # Sample Agoda search URL (you can replace this with an actual Agoda search URL)
    # This is a generic format - you'll need to replace with actual search parameters
    search_url = "https://www.agoda.com/search?city=6667&checkIn=2024-03-15&checkOut=2024-03-17&adults=2&children=0&rooms=1"
    
    print("=" * 60)
    print("AGODA HOTEL SCRAPER TEST")
    print("=" * 60)
    print(f"Testing with URL: {search_url}")
    print()
    
    # Initialize scraper
    try:
        print("Initializing scraper...")
        scraper = AgodaHotelScraper(headless=True)  # Use headless mode for testing
        print("✓ Scraper initialized successfully")
        
        # Test URL parsing functions
        print("\nTesting URL parsing functions:")
        print(f"Platform: {scraper.platform_from_url(search_url)}")
        print(f"City: {scraper.city_from_url(search_url)}")
        print(f"Country: {scraper.country_from_url(search_url)}")
        print(f"Check-in: {scraper.checkin_from_url(search_url)}")
        print(f"Check-out: {scraper.checkout_from_url(search_url)}")
        print(f"Adults: {scraper.adults_from_url(search_url)}")
        print(f"Children: {scraper.children_from_url(search_url)}")
        
        # Test text cleaning
        print("\nTesting text cleaning:")
        test_texts = ["Rs. 1,500", "25%", "  Extra spaces  \n", "Normal text"]
        for text in test_texts:
            cleaned = scraper.clean_text(text)
            print(f"'{text}' → '{cleaned}'")
        
        # Test number conversion
        print("\nTesting number conversion:")
        for text in test_texts:
            number = scraper.convert_to_number(text)
            print(f"'{text}' → {number}")
        
        print("\n" + "=" * 60)
        print("STARTING SCRAPING TEST")
        print("=" * 60)
        
        # Start scraping (limit to 1 page for testing)
        hotels_data = scraper.scrape_hotels(
            search_url=search_url,
            customer_required_max_nights=30,
            max_pages=1  # Limit to 1 page for testing
        )
        
        print(f"\n✓ Scraping completed!")
        print(f"Total hotels scraped: {len(hotels_data)}")
        
        if hotels_data:
            print("\nSample hotel data (first hotel):")
            first_hotel = hotels_data[0]
            for key, value in first_hotel.items():
                if isinstance(value, list) and len(value) > 3:
                    print(f"  {key}: {value[:3]}... (truncated)")
                else:
                    print(f"  {key}: {value}")
        
        # Save to DataFrame and CSV
        print("\nSaving data...")
        df = scraper.save_to_csv("test_agoda_hotels.csv")
        
        print(f"✓ Data saved to test_agoda_hotels.csv")
        print(f"DataFrame shape: {df.shape}")
        print(f"Columns: {list(df.columns)}")
        
        return len(hotels_data)
        
    except Exception as e:
        print(f"✗ Error during scraping: {e}")
        logger.error(f"Scraping error: {e}")
        return 0
    
    finally:
        # Clean up
        try:
            del scraper
            print("✓ Scraper cleaned up")
        except:
            pass

def test_with_mock_data():
    """Test with mock data when actual scraping fails"""
    print("\n" + "=" * 60)
    print("TESTING WITH MOCK DATA")
    print("=" * 60)
    
    # Create mock hotel data
    mock_hotels = []
    for i in range(5):
        mock_hotel = {
            'property_id': f"{i+1:02d}",
            'property_name': f'Test Hotel {i+1}',
            'Platform': 'Agoda',
            'property_type': 'Hotel',
            'Location': f'Test Location {i+1}',
            'City': 'Test City',
            'Country': 'Test Country',
            'zip_code': f'12345{i}',
            'star_rating': 4.0 + (i * 0.2),
            'review_score': 8.0 + (i * 0.3),
            'review_count': f'{100 + i*50} reviews',
            'Check-in': '2024-03-15',
            'Checkout_date': '2024-03-17',
            'scraped_date': '2024-01-20',
            'booking_window_days': 54,
            'amenities': ['WiFi', 'Pool', 'Gym'],
            'room_type_name': ['Deluxe Room', 'Standard Room'],
            'room_description': ['Spacious room with city view'],
            'room_size_sqm': ['25 sqm'],
            'bed_type': ['King Bed'],
            'latitude': 40.7128 + (i * 0.01),
            'longitude': -74.0060 + (i * 0.01),
            'room_capacity_adults': 2,
            'room_capacity_children': 0,
            'price_per_night': [1500.0 + (i * 100)],
            'original_price': [2000.0 + (i * 100)],
            'discount_percent': ['25'],
            'price_per_adult': [750.0 + (i * 50)],
            'cancellation_policy': ['Free cancellation'],
            'refundable': ['Refundable'],
            'availability_status': 'Our last 2 Rooms',
            'min_stay_nights': 0,
            'max_stay_nights': 30,
            'mobile_discount_flag': 0,
            'loyalty_program_flag': 0,
            'url': f'https://www.agoda.com/hotel/test-hotel-{i+1}'
        }
        mock_hotels.append(mock_hotel)
    
    # Save mock data
    import pandas as pd
    df = pd.DataFrame(mock_hotels)
    df.to_csv("mock_agoda_hotels.csv", index=False)
    
    print(f"✓ Created mock data with {len(mock_hotels)} hotels")
    print(f"✓ Saved to mock_agoda_hotels.csv")
    print(f"DataFrame shape: {df.shape}")
    print(f"Columns: {list(df.columns)}")
    
    return len(mock_hotels)

if __name__ == "__main__":
    print("Starting Agoda Scraper Test...")
    
    # Test the scraper
    scraped_count = test_agoda_scraper()
    
    # If scraping failed, test with mock data
    if scraped_count == 0:
        print("\nActual scraping failed, testing with mock data...")
        mock_count = test_with_mock_data()
        print(f"\nMock test completed with {mock_count} hotels")
    else:
        print(f"\nScraping test completed successfully with {scraped_count} hotels")
    
    print("\n" + "=" * 60)
    print("TEST COMPLETED")
    print("=" * 60)