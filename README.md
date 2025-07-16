# Agoda Hotel Scraper - Improved Version

This is an improved version of the Agoda hotel scraper that extracts comprehensive hotel data including categories, prices, ratings, and more from Agoda.com.

## Features

✅ **Category Extraction**: Extracts hotel categories/room types using the `data-selenium="masterroom-title-name"` selector  
✅ **Comprehensive Data**: Collects hotel names, prices, ratings, categories, locations, amenities, and review counts  
✅ **Object-Oriented Design**: Clean, modular code structure with error handling  
✅ **Multiple Output Formats**: Saves data in both CSV and JSON formats  
✅ **Robust Error Handling**: Handles various scraping errors gracefully  
✅ **Debug Support**: Automatically saves debug files when issues occur  
✅ **Pagination Support**: Automatically loads more hotels from multiple pages  
✅ **Anti-Detection**: Includes user-agent rotation and headless browsing  

## Installation

1. Install the required dependencies:
```bash
pip install -r requirements.txt
```

2. Make sure you have Firefox installed (for Selenium WebDriver)

## Usage

### Basic Usage

```python
from agoda_scraper_improved import AgodaScraper

# Initialize scraper
scraper = AgodaScraper()

# Scrape hotels
url = "YOUR_AGODA_SEARCH_URL"
success = scraper.scrape_hotels(url, max_iterations=3)

if success:
    scraper.save_data()  # Saves to CSV and JSON
else:
    print("Scraping failed!")

# Always cleanup
scraper.cleanup()
```

### Quick Start with Demo

Run the demo script to see the scraper in action:

```bash
python demo_agoda_scraper.py
```

### Advanced Usage

```python
from agoda_scraper_improved import AgodaScraper

scraper = AgodaScraper()

try:
    # Scrape hotels with custom settings
    success = scraper.scrape_hotels(url, max_iterations=5)
    
    if success:
        # Access scraped data
        hotels = scraper.hotels_data
        
        # Filter by category
        luxury_hotels = [h for h in hotels if h['category'] and 'suite' in h['category'].lower()]
        
        # Filter by price range
        budget_hotels = [h for h in hotels if h['price'] and 'Rs' in h['price']]
        
        # Save data
        scraper.save_data()
        
        print(f"Found {len(luxury_hotels)} luxury hotels")
        print(f"Found {len(budget_hotels)} budget hotels")
        
except Exception as e:
    print(f"Error: {e}")
finally:
    scraper.cleanup()
```

## Data Structure

The scraper extracts the following information for each hotel:

```python
{
    "hotel_id": "unique_hotel_identifier",
    "name": "Hotel Name",
    "price": "₹5,000 per night",
    "rating": "8.5",
    "category": "Deluxe Suite",  # NEW: Room category/type
    "location": "City Center, Darjeeling",
    "amenities": ["Free WiFi", "Pool", "Spa"],
    "review_count": "1,234 reviews"
}
```

## Key Improvements

### 1. Category Extraction
The scraper now extracts hotel categories/room types using multiple selectors:
- `[data-selenium="masterroom-title-name"]` (primary selector you requested)
- `.Box-sc-kv6pi1-0.jJvGxG` (specific class you mentioned)
- Various fallback selectors for robustness

### 2. Enhanced Data Collection
- **Location**: Hotel location/address
- **Amenities**: List of hotel facilities
- **Review Count**: Number of reviews
- **Better Price Detection**: Handles different price formats (₹, Rs, INR)

### 3. Improved Architecture
- **Class-based Design**: Organized into `AgodaScraper` class
- **Modular Methods**: Separate methods for each data type extraction
- **Better Error Handling**: Graceful handling of missing elements
- **Debug Support**: Automatic debug file generation

### 4. Multiple Output Formats
- **CSV**: `agoda_hotels_improved.csv` - for spreadsheet analysis
- **JSON**: `agoda_hotels_improved.json` - for programmatic use
- **Summary**: Detailed statistics and sample data

## Configuration

### Scraper Settings
You can customize the scraper behavior:

```python
scraper = AgodaScraper()

# Adjust iterations (more = more hotels, slower)
scraper.scrape_hotels(url, max_iterations=5)

# The scraper automatically:
# - Uses headless Firefox
# - Handles pagination
# - Avoids duplicate hotels
# - Scrolls to load more content
```

### CSS Selectors
The scraper uses multiple fallback selectors for robustness:

```python
# Category selectors (in order of preference)
category_selectors = [
    '[data-selenium="masterroom-title-name"]',  # Your requested selector
    '.Box-sc-kv6pi1-0.jJvGxG',                # Your specific class
    '[class*="masterroom"]',
    '[class*="room-type"]',
    '[class*="category"]'
]
```

## Output Files

When you run the scraper, it creates:

1. **`agoda_hotels_improved.csv`** - Main data in CSV format
2. **`agoda_hotels_improved.json`** - Structured data in JSON format
3. **Debug files** (if issues occur):
   - `timeout_page_source.html` - Page source if timeout
   - `debug_no_hotels_iter_X.html` - Debug info if no hotels found

## Troubleshooting

### Common Issues

1. **No hotels found**: Check the URL and ensure it's a valid Agoda search
2. **Timeout errors**: Increase the timeout or check internet connection
3. **Missing categories**: The category selector might have changed, check debug files

### Debug Mode

The scraper automatically saves debug information:
- Page source when errors occur
- Detailed logging to console
- Sample HTML for troubleshooting

### Performance Tips

1. **Adjust iterations**: Start with 2-3 iterations, increase if needed
2. **Monitor output**: Check the console for progress updates
3. **Use stable internet**: Ensure reliable connection for scraping

## Legal Considerations

⚠️ **Important**: Always ensure you comply with:
- Agoda's Terms of Service
- robots.txt requirements
- Local scraping laws
- Rate limiting best practices

## Support

If you encounter issues:
1. Check the debug files generated
2. Review the console logs
3. Ensure all dependencies are installed
4. Verify the URL is correct

## Example Output

```
🏨 SCRAPING RESULTS FOR DARJEELING 🏨
============================================================
📊 Statistics:
   Total Hotels: 45
   With Categories: 32 (71.1%)
   With Prices: 43 (95.6%)
   With Ratings: 38 (84.4%)

🏷️  Category Examples:
   1. Deluxe Room
   2. Superior Suite
   3. Standard Room
   4. Premium Suite
   5. Executive Room

🏨 Sample Hotels with Categories:
   1. Hotel Darjeeling Palace...
      Category: Deluxe Room
      Price: ₹4,500 per night
      Rating: 8.2
```

## License

This project is for educational purposes. Please use responsibly and in accordance with applicable laws and website terms of service.