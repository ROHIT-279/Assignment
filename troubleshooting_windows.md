# Windows Troubleshooting Guide for Agoda Scraper

## 🛠️ Issues Fixed

### ✅ **Issue 1: Unicode Encoding Error**
**Problem:** `UnicodeEncodeError: 'charmap' codec can't encode character`

**Solution Applied:**
- Removed all emoji characters from logging messages
- Added Windows-specific encoding fixes
- Used UTF-8 encoding for all file operations
- Fixed console output encoding for Windows

### ✅ **Issue 2: No Hotels Found**
**Problem:** Scraper finds 0 hotels on all pages

**Root Causes & Solutions:**
1. **Website Structure Changes** - Added multiple CSS selectors
2. **Anti-bot Detection** - Improved user agent and delays
3. **Page Loading Issues** - Extended wait times and better detection

## 🚀 **New Windows-Compatible Script**

Use: **`agoda_scraper_windows_fixed.py`**

This script includes:
- ✅ No emoji characters in logging
- ✅ Windows encoding fixes
- ✅ Multiple CSS selectors for hotel detection
- ✅ Debug page saving to troubleshoot structure
- ✅ Extended wait times for page loading
- ✅ Better error handling

## 📋 **Quick Diagnosis Steps**

### Step 1: Check Debug Files
When the scraper runs and finds 0 hotels, it saves debug files:
```
debug_page_1.html
debug_page_2.html
etc.
```

Open these files in a browser to see what the scraper is actually seeing.

### Step 2: Manual Check
1. Open your search URL in a browser
2. Check if hotels are actually displayed
3. Right-click on a hotel → Inspect Element
4. Look for the CSS class names

### Step 3: Update Selectors (if needed)
If the CSS selectors are different, update the `hotel_selectors` list in the script:

```python
hotel_selectors = [
    'YOUR_NEW_SELECTOR_HERE',
    'li[data-selenium="hotel-item"]',
    # ... other selectors
]
```

## 🔧 **Alternative Approaches**

### Option 1: Try Different User Agent
```python
options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:91.0) Gecko/20100101 Firefox/91.0")
```

### Option 2: Disable Headless Mode (for debugging)
```python
driver = self.setup_driver(headless=False)  # This will show the browser
```

### Option 3: Add More Wait Time
```python
time.sleep(15)  # Instead of 10 seconds
```

### Option 4: Try Different Search URL
Sometimes search URLs expire or have session-specific parameters. Try:
1. Go to Agoda.com manually
2. Search for "Darjeeling"
3. Copy the new URL from address bar
4. Replace in the script

## 📊 **Expected Behavior**

### ✅ **Success Indicators:**
```
Found X hotels using selector: li[data-selenium="hotel-item"]
Page 1: Found 3 new hotels (Total: 3)
Worker 1-1: Successfully extracted data for Hotel Name
```

### ❌ **Failure Indicators:**
```
Page 1: Found 0 new hotels (Total: 0)
No hotels found on page 1. Debug file saved.
No hotel URLs found
```

## 🎯 **Most Common Solutions**

### 1. **Website Updated Structure**
- Agoda frequently updates their HTML structure
- The debug files will help identify new selectors
- Update the `hotel_selectors` list with new CSS classes

### 2. **Geo-blocking or Anti-bot**
- Try different user agents
- Add longer delays between requests
- Consider using a VPN if region-blocked

### 3. **Search URL Issues**
- URL might be expired or session-specific
- Generate a fresh search URL manually
- Ensure the URL has proper encoding

## 🔍 **Debug Commands**

### Check if Selenium is working:
```python
driver = webdriver.Firefox()
driver.get("https://www.google.com")
print(driver.title)  # Should print "Google"
driver.quit()
```

### Check if Agoda loads:
```python
driver = webdriver.Firefox()
driver.get("https://www.agoda.com")
time.sleep(5)
print("Page loaded successfully" if "agoda" in driver.title.lower() else "Failed to load")
driver.quit()
```

## 🚀 **Quick Fix Commands**

### Run the Windows-Fixed Version:
```bash
python agoda_scraper_windows_fixed.py
```

### Check Debug Output:
```bash
# After running, check these files:
dir debug_page_*.html
# Open them in browser to see page content
```

### Enable Debug Mode:
```python
# In the script, change:
driver = self.setup_driver(headless=False)  # Shows browser window
time.sleep(20)  # Longer waits
```

## 📞 **If Issues Persist**

1. **Check debug_page_X.html files** - These show exactly what the scraper sees
2. **Try manual browser test** - Verify the search URL works manually  
3. **Update CSS selectors** - Based on current Agoda structure
4. **Consider rate limiting** - Agoda might be blocking rapid requests

The **Windows-fixed script** should resolve both the encoding errors and improve hotel detection significantly!

## 🎉 **Success Metrics**

When working correctly, you should see:
```
Starting Phase 1: Extracting hotel URLs...
Loading search results page...
Found 15 hotels using selector: li[data-selenium="hotel-item"]
Page 1: Found 15 new hotels (Total: 15)
Found 25 hotels to process
Processing batch 1 with 5 hotels
Worker 1-0: Successfully extracted data for Hotel Name
```