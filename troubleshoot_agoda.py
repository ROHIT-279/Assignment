#!/usr/bin/env python3
"""
Troubleshooting script for Agoda scraping issues
This script diagnoses common problems with Agoda page loading
"""

from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import time
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def troubleshoot_agoda_url(url):
    """Comprehensive troubleshooting for Agoda URL"""
    
    print("🔍 AGODA TROUBLESHOOTING DIAGNOSTIC")
    print("=" * 50)
    
    # Setup basic driver
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    
    driver = None
    
    try:
        print("1. Initializing Firefox driver...")
        driver = webdriver.Firefox(options=options)
        print("✅ Driver initialized successfully")
        
        print(f"\n2. Loading URL...")
        print(f"URL: {url[:100]}...")
        driver.get(url)
        
        # Wait for basic page load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        # Basic page info
        print(f"✅ Page loaded")
        print(f"Current URL: {driver.current_url}")
        print(f"Page title: {driver.title}")
        print(f"Page source length: {len(driver.page_source)} characters")
        
        # Check for common blocking indicators
        print(f"\n3. Checking for blocking...")
        page_title_lower = driver.title.lower()
        blocking_keywords = ['blocked', 'access denied', 'forbidden', 'error', 'captcha']
        found_blocking = [kw for kw in blocking_keywords if kw in page_title_lower]
        
        if found_blocking:
            print(f"⚠️  Possible blocking detected: {found_blocking}")
        else:
            print("✅ No obvious blocking detected")
        
        # Check for hotel-related content
        print(f"\n4. Checking for hotel content...")
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        hotel_keywords = ['hotel', 'property', 'accommodation', 'booking', 'room', 'suite']
        found_keywords = []
        page_text = soup.get_text().lower()
        
        for keyword in hotel_keywords:
            count = page_text.count(keyword)
            if count > 0:
                found_keywords.append(f"{keyword}({count})")
        
        print(f"Hotel keywords found: {', '.join(found_keywords)}")
        
        # Test various hotel selectors
        print(f"\n5. Testing hotel selectors...")
        hotel_selectors = [
            'li[data-selenium="hotel-item"]',
            '[data-selenium="hotel-item"]',
            '.hotel-item',
            '[data-testid="property-card"]',
            '.property-card',
            '[class*="hotel"]',
            'div[data-hotelid]',
            'article',
            '.search-result'
        ]
        
        working_selectors = []
        for selector in hotel_selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    working_selectors.append(f"{selector} ({len(elements)} elements)")
                    print(f"✅ {selector}: {len(elements)} elements")
                else:
                    print(f"❌ {selector}: 0 elements")
            except Exception as e:
                print(f"❌ {selector}: ERROR - {str(e)}")
        
        # Wait and try again after some time
        print(f"\n6. Waiting for dynamic content (10 seconds)...")
        time.sleep(10)
        
        print(f"\n7. Re-testing after wait...")
        working_selectors_after = []
        for selector in hotel_selectors[:3]:  # Test top 3 only
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    working_selectors_after.append(f"{selector} ({len(elements)} elements)")
                    print(f"✅ {selector}: {len(elements)} elements")
            except Exception as e:
                print(f"❌ {selector}: ERROR")
        
        # Category-specific testing
        print(f"\n8. Testing category selectors...")
        category_selectors = [
            '[data-selenium="masterroom-title-name"]',
            '.Box-sc-kv6pi1-0.jJvGxG',
            '[class*="masterroom"]',
            '[class*="room-type"]',
            '[class*="category"]'
        ]
        
        for selector in category_selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    print(f"✅ Category selector {selector}: {len(elements)} elements")
                    # Show sample text
                    sample_text = elements[0].text.strip()[:50] if elements[0].text.strip() else "No text"
                    print(f"   Sample: {sample_text}")
                else:
                    print(f"❌ Category selector {selector}: 0 elements")
            except Exception as e:
                print(f"❌ Category selector {selector}: ERROR")
        
        # Save debug page
        print(f"\n9. Saving debug page...")
        with open("troubleshoot_debug.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        print("✅ Debug page saved as 'troubleshoot_debug.html'")
        
        # Final recommendations
        print(f"\n🎯 RECOMMENDATIONS:")
        if not working_selectors:
            print("❌ No hotel selectors worked!")
            print("   - The URL might not be loading hotels properly")
            print("   - Try a different Agoda search URL")
            print("   - Check if you need to accept cookies or solve captcha")
            print("   - Agoda might be blocking automated access")
        else:
            print("✅ Some selectors worked!")
            print("   - Use the robust scraper with multiple selector fallbacks")
            print(f"   - Working selectors: {working_selectors}")
        
        if found_keywords:
            print("✅ Hotel content detected - page seems legitimate")
        else:
            print("⚠️  No hotel content detected - might be blocked or wrong page")
        
        print(f"\n📄 Debug file created: troubleshoot_debug.html")
        print("   - Open this file to manually inspect the page content")
        
    except Exception as e:
        print(f"❌ Error during troubleshooting: {str(e)}")
        
    finally:
        if driver:
            driver.quit()
            print("🔧 Driver closed")

def quick_test():
    """Quick test with the problematic URL"""
    url = "https://www.agoda.com/en-in/search?guid=ac34b805-fbbb-4a54-91f6-72bd44251297&asq=oSBZUdCJkTqIcAJrG1AX8Jufa9Vwpz6XltTHq4n%2B9gNpSLc%2BT%2BpB%2F8FnmmA8sOyAJ0WZY5hpLWEr%2Fk8qr78gW4DMS7e7llLtqq76yKsoLJ2OoQ3gw8ln%2FUAwfEcSpHO4IoT8r2EKxXsqX%2FNiA5fxsgqQMycviD3CIWSJVwpQ8sqLB7kVtS1F64bq7yiJpY541pwsBzifP5NpR6wrJ1u54kHb%2BKC2e3zym6tmyvlzCzM%3D&city=10863&tick=638881978745&locale=en-in&ckuid=0782016a-40d3-4e7a-86a4-8cab9dacec41&prid=0&gclid=Cj0KCQjw-NfDBhDyARIsAD-ILeBXva5TJhq-jGK3Si0BOfvtLo82iIstmv4-XMoqfU56Mshxz_UezUkaAhwMEALw_wcB&currency=INR&correlationId=55168ae7-8bc1-4224-a8eb-86ba246be729&analyticsSessionId=-1950121884218971931&pageTypeId=1&realLanguageId=15&languageId=1&origin=IN&stateCode=WB&cid=1922885&tag=6f147157-60b8-459f-af1a-9935d44970e9&userId=0782016a-40d3-4e7a-86a4-8cab9dacec41&whitelabelid=1&loginLvl=0&storefrontId=3&currencyId=27&currencyCode=INR&htmlLanguage=en-in&cultureInfoName=en-in&machineName=sg-pc-6h-acm-web-user-8697c4cd7c-gmgqx&trafficGroupId=5&trafficSubGroupId=122&aid=82361&useFullPageLogin=true&cttp=4&isRealUser=true&mode=production&browserFamily=Chrome&cdnDomain=agoda.net&checkIn=2025-08-12&checkOut=2025-08-13&rooms=1&adults=2&children=0&priceCur=INR&los=1&textToSearch=Darjeeling&travellerType=1&familyMode=off&ds=cgN73pCK5wrspJ7h&productType=-1"
    
    troubleshoot_agoda_url(url)

if __name__ == "__main__":
    quick_test()