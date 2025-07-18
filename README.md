# Agoda Hotel Scraper - Enhanced Multi-threaded Version

This enhanced Agoda scraper extracts detailed hotel information including room categories, prices, customer reviews, and ratings using multi-threading for efficient data collection.

## ✨ Features

- **Multi-threaded Processing**: Processes 5 hotels simultaneously in parallel
- **Comprehensive Data Extraction**: 
  - Hotel names and URLs
  - Overall ratings
  - Room categories and prices
  - Customer reviews with ratings and dates
  - Reviewer information
- **Intelligent Scrolling**: Automatically scrolls through search pages
- **Robust Error Handling**: Continues processing even if individual hotels fail
- **Progress Tracking**: Real-time logging and progress updates
- **Batch Processing**: Processes hotels in batches of 5 with intermediate saves
- **Multiple Output Formats**: CSV and JSON outputs
- **Resume Capability**: Tracks processed hotels to avoid duplicates

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Search Page   │───▶│  Extract URLs   │───▶│ Multi-threaded │
│   Scraping      │    │  (With Scroll)  │    │  Processing     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                       │
                                               ┌───────▼────────┐
                                               │  Batch 1 (5)   │
                                               │  Batch 2 (5)   │
                                               │  Batch N (5)   │
                                               └───────┬────────┘
                                                       │
                                               ┌───────▼────────┐
                                               │ CSV + JSON     │
                                               │ Output Files   │
                                               └────────────────┘
```

## 📋 Prerequisites

### System Requirements
- Python 3.7+
- Firefox Browser
- Geckodriver
- Sufficient RAM (4GB+ recommended)
- Stable internet connection

### Dependencies
```
selenium==4.15.2
beautifulsoup4==4.12.2
lxml==4.9.3
requests==2.31.0
pandas==2.1.3
webdriver-manager==4.0.1
```

## 🚀 Quick Setup

### Option 1: Automated Setup
```bash
python setup_and_run.py
```

### Option 2: Manual Setup

1. **Install Python dependencies:**
```bash
pip install -r requirements.txt
```

2. **Install Firefox:**
```bash
# Ubuntu/Debian
sudo apt-get install firefox

# CentOS/RHEL
sudo yum install firefox

# macOS
brew install --cask firefox
```

3. **Install Geckodriver:**
```bash
# Linux
wget https://github.com/mozilla/geckodriver/releases/download/v0.33.0/geckodriver-v0.33.0-linux64.tar.gz
tar -xzf geckodriver-v0.33.0-linux64.tar.gz
sudo mv geckodriver /usr/local/bin/
sudo chmod +x /usr/local/bin/geckodriver

# macOS
brew install geckodriver
```

## 🎯 Usage

### Basic Usage
```bash
python agoda_scraper_optimized.py
```

### Configuration Options

Edit the `main()` function in `agoda_scraper_optimized.py`:

```python
def main():
    search_url = "YOUR_AGODA_SEARCH_URL"
    scraper = AgodaScraperOptimized(max_workers=5)
    
    # Limit hotels for testing (remove for full scraping)
    scraper.run_scraper(search_url, max_hotels=25)
```

**Parameters:**
- `max_workers`: Number of parallel threads (default: 5)
- `max_hotels`: Limit number of hotels to process (None for all)
- `headless`: Run browser in background (True/False)

### Custom Search URL
Replace the search URL in the script with your Agoda search results URL. Make sure it includes:
- Location/city
- Check-in/check-out dates
- Number of guests
- Any filters you want to apply

## 📊 Output Files

The scraper generates multiple output files:

### 1. Final CSV Output
**File**: `agoda_hotels_final_YYYYMMDD_HHMMSS.csv`

**Columns:**
| Column | Description |
|--------|-------------|
| hotel_name | Name of the hotel |
| hotel_url | Direct link to hotel page |
| overall_rating | Hotel's overall rating |
| extraction_timestamp | When data was extracted |
| room_category | Type of room |
| room_price | Price of the room |
| reviewer_info | Information about reviewer |
| room_type_reviewed | Room type mentioned in review |
| review_rating | Individual review rating |
| review_date | Date of the review |
| review_comment | Full review text |

### 2. Batch CSV Files
**Files**: `agoda_batch_X_YYYYMMDD_HHMMSS.csv`
- Intermediate results for each batch
- Useful for monitoring progress
- Can be used to resume if main process fails

### 3. JSON Backup
**File**: `agoda_raw_data_YYYYMMDD_HHMMSS.json`
- Complete raw data in JSON format
- Includes nested structure
- Useful for further processing

### 4. Log File
**File**: `agoda_scraper.log`
- Detailed execution logs
- Error messages and warnings
- Progress tracking information

## 🔧 Advanced Configuration

### Selenium Options
Modify `setup_driver()` method for custom browser settings:

```python
def setup_driver(self, headless=True):
    options = Options()
    if headless:
        options.add_argument("--headless")
    
    # Add custom options
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-gpu")
    # ... more options
```

### CSS Selectors Customization
The scraper uses specific CSS selectors matching Agoda's structure:

```python
# Hotel URL selector
hotel_link = hotel.find('a', {'data-testid': 'property-name-link'})

# Room category selector  
category_elem = room_elem.find('div', {'data-info-type': 'room-type'})

# Review sections
review_sections = soup.find_all('div', class_=lambda x: x and 'Review-comment-bubble' in x)
```

### Threading Configuration
Adjust for your system capabilities:

```python
# Conservative (lower system load)
scraper = AgodaScraperOptimized(max_workers=3)

# Aggressive (higher performance)
scraper = AgodaScraperOptimized(max_workers=8)
```

## 🐛 Troubleshooting

### Common Issues

**1. Geckodriver not found**
```
selenium.common.exceptions.WebDriverException: 'geckodriver' executable needs to be in PATH
```
**Solution**: Install geckodriver and add to PATH

**2. Firefox not found**
```
selenium.common.exceptions.WebDriverException: Message: Process unexpectedly closed with status 1
```
**Solution**: Install Firefox browser

**3. Timeout errors**
```
selenium.common.exceptions.TimeoutException
```
**Solution**: Increase timeout values or check internet connection

**4. Memory issues**
```
MemoryError or system slowdown
```
**Solution**: Reduce max_workers or max_hotels

### Performance Optimization

**1. Reduce headless browser count:**
```python
scraper = AgodaScraperOptimized(max_workers=3)  # Instead of 5
```

**2. Add delays between batches:**
```python
time.sleep(60)  # Increase from 30 seconds
```

**3. Process smaller batches:**
```python
scraper.run_scraper(search_url, max_hotels=50)  # Limit hotels
```

## 📈 Monitoring Progress

### Real-time Monitoring
```bash
# Watch log file
tail -f agoda_scraper.log

# Monitor CSV files
ls -la agoda_batch_*.csv
```

### Progress Indicators
- ✅ Successful extraction
- ❌ Failed extraction  
- 🔄 Processing batch
- 💾 Saving batch results
- ⏸️ Pausing between batches

## ⚖️ Ethical Considerations

- **Respect robots.txt**: Check Agoda's robots.txt policy
- **Rate limiting**: Built-in delays prevent overwhelming servers
- **Personal use**: Use responsibly and for legitimate purposes
- **Data privacy**: Handle extracted data according to privacy laws

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make improvements
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is for educational purposes. Please respect Agoda's terms of service and use responsibly.

## 🆘 Support

If you encounter issues:

1. Check the troubleshooting section
2. Review log files for detailed errors
3. Ensure all prerequisites are installed
4. Try with a smaller dataset first

## 🔄 Updates and Improvements

### Current Version Features:
- ✅ Multi-threaded processing
- ✅ Robust error handling
- ✅ Progress tracking
- ✅ Multiple output formats
- ✅ Batch processing
- ✅ Resume capability

### Future Enhancements:
- Database storage support
- GUI interface
- Docker containerization
- API endpoints
- Enhanced filtering options