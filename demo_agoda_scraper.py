#!/usr/bin/env python3
"""
Demo script for the improved Agoda scraper
This script shows how to use the AgodaScraper class to scrape hotel data
"""

from agoda_scraper_improved import AgodaScraper
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def demo_scraper():
    """Demo function to show how to use the scraper"""
    
    # Example URLs for different destinations
    urls = {
        "Darjeeling": "https://www.agoda.com/en-in/search?guid=ac34b805-fbbb-4a54-91f6-72bd44251297&asq=oSBZUdCJkTqIcAJrG1AX8Jufa9Vwpz6XltTHq4n%2B9gNpSLc%2BT%2BpB%2F8FnmmA8sOyAJ0WZY5hpLWEr%2Fk8qr78gW4DMS7e7llLtqq76yKsoLJ2OoQ3gw8ln%2FUAwfEcSpHO4IoT8r2EKxXsqX%2FNiA5fxsgqQMycviD3CIWSJVwpQ8sqLB7kVtS1F64bq7yiJpY541pwsBzifP5NpR6wrJ1u54kHb%2BKC2e3zym6tmyvlzCzM%3D&city=10863&tick=638881978745&locale=en-in&ckuid=0782016a-40d3-4e7a-86a4-8cab9dacec41&prid=0&gclid=Cj0KCQjw-NfDBhDyARIsAD-ILeBXva5TJhq-jGK3Si0BOfvtLo82iIstmv4-XMoqfU56Mshxz_UezUkaAhwMEALw_wcB&currency=INR&correlationId=55168ae7-8bc1-4224-a8eb-86ba246be729&analyticsSessionId=-1950121884218971931&pageTypeId=1&realLanguageId=15&languageId=1&origin=IN&stateCode=WB&cid=1922885&tag=6f147157-60b8-459f-af1a-9935d44970e9&userId=0782016a-40d3-4e7a-86a4-8cab9dacec41&whitelabelid=1&loginLvl=0&storefrontId=3&currencyId=27&currencyCode=INR&htmlLanguage=en-in&cultureInfoName=en-in&machineName=sg-pc-6h-acm-web-user-8697c4cd7c-gmgqx&trafficGroupId=5&trafficSubGroupId=122&aid=82361&useFullPageLogin=true&cttp=4&isRealUser=true&mode=production&browserFamily=Chrome&cdnDomain=agoda.net&checkIn=2025-08-12&checkOut=2025-08-13&rooms=1&adults=2&children=0&priceCur=INR&los=1&textToSearch=Darjeeling&travellerType=1&familyMode=off&ds=cgN73pCK5wrspJ7h&productType=-1"
    }
    
    # Choose destination
    destination = "Darjeeling"
    url = urls[destination]
    
    logger.info(f"Starting scraping for {destination}")
    
    # Initialize scraper
    scraper = AgodaScraper()
    
    try:
        # Scrape hotels (adjust max_iterations as needed)
        success = scraper.scrape_hotels(url, max_iterations=2)
        
        if success:
            logger.info("Scraping completed successfully!")
            
            # Save data
            scraper.save_data()
            
            # Print detailed results
            print(f"\n🏨 SCRAPING RESULTS FOR {destination.upper()} 🏨")
            print("="*60)
            
            if scraper.hotels_data:
                # Show some statistics
                total_hotels = len(scraper.hotels_data)
                with_categories = len([h for h in scraper.hotels_data if h['category']])
                with_prices = len([h for h in scraper.hotels_data if h['price']])
                with_ratings = len([h for h in scraper.hotels_data if h['rating']])
                
                print(f"📊 Statistics:")
                print(f"   Total Hotels: {total_hotels}")
                print(f"   With Categories: {with_categories} ({with_categories/total_hotels*100:.1f}%)")
                print(f"   With Prices: {with_prices} ({with_prices/total_hotels*100:.1f}%)")
                print(f"   With Ratings: {with_ratings} ({with_ratings/total_hotels*100:.1f}%)")
                
                # Show category breakdown
                categories = [h['category'] for h in scraper.hotels_data if h['category']]
                if categories:
                    print(f"\n🏷️  Category Examples:")
                    unique_categories = list(set(categories))[:10]  # Show first 10 unique categories
                    for i, category in enumerate(unique_categories, 1):
                        print(f"   {i}. {category}")
                
                # Show sample hotels with categories
                print(f"\n🏨 Sample Hotels with Categories:")
                hotels_with_categories = [h for h in scraper.hotels_data if h['category']][:5]
                for i, hotel in enumerate(hotels_with_categories, 1):
                    print(f"   {i}. {hotel['name'][:40]}...")
                    print(f"      Category: {hotel['category']}")
                    print(f"      Price: {hotel['price']}")
                    print(f"      Rating: {hotel['rating']}")
                    print()
                
            else:
                logger.warning("No hotel data was collected!")
                
        else:
            logger.error("Scraping failed!")
            
    except KeyboardInterrupt:
        logger.info("Scraping interrupted by user")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
    finally:
        scraper.cleanup()

def custom_scraper_example():
    """Example of how to use scraper with custom settings"""
    
    # Custom URL for different destination
    custom_url = "YOUR_CUSTOM_AGODA_URL_HERE"
    
    # Initialize scraper
    scraper = AgodaScraper()
    
    try:
        # Scrape with custom settings
        success = scraper.scrape_hotels(custom_url, max_iterations=5)  # More iterations
        
        if success:
            # Custom data processing
            hotels = scraper.hotels_data
            
            # Filter hotels with specific criteria
            luxury_hotels = [h for h in hotels if h['category'] and 'suite' in h['category'].lower()]
            budget_hotels = [h for h in hotels if h['price'] and 'Rs' in h['price']]
            
            print(f"Found {len(luxury_hotels)} luxury hotels")
            print(f"Found {len(budget_hotels)} budget hotels")
            
            # Save data
            scraper.save_data()
            
    except Exception as e:
        logger.error(f"Custom scraping error: {str(e)}")
    finally:
        scraper.cleanup()

if __name__ == "__main__":
    print("🚀 Agoda Scraper Demo")
    print("=" * 50)
    
    # Run the demo
    demo_scraper()
    
    # Uncomment to run custom example
    # custom_scraper_example()