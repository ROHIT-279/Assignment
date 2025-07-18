#!/usr/bin/env python3
"""
Agoda Scraper Setup and Runner
This script helps set up the environment and run the Agoda scraper
"""

import subprocess
import sys
import os
from pathlib import Path

def install_requirements():
    """Install required packages"""
    print("📦 Installing required packages...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✅ Successfully installed all requirements!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error installing requirements: {e}")
        return False

def check_firefox():
    """Check if Firefox is installed"""
    print("🔍 Checking for Firefox installation...")
    try:
        # Try to find firefox executable
        if os.system("which firefox > /dev/null 2>&1") == 0:
            print("✅ Firefox found!")
            return True
        else:
            print("❌ Firefox not found. Please install Firefox browser.")
            print("   Ubuntu/Debian: sudo apt-get install firefox")
            print("   CentOS/RHEL: sudo yum install firefox")
            print("   macOS: brew install --cask firefox")
            return False
    except Exception as e:
        print(f"❌ Error checking Firefox: {e}")
        return False

def setup_geckodriver():
    """Instructions for geckodriver setup"""
    print("🔧 Geckodriver Setup Instructions:")
    print("   1. Download geckodriver from: https://github.com/mozilla/geckodriver/releases")
    print("   2. Extract and move to /usr/local/bin/ (or add to PATH)")
    print("   3. Make it executable: chmod +x /usr/local/bin/geckodriver")
    print("")
    print("   Quick install (Linux):")
    print("   wget https://github.com/mozilla/geckodriver/releases/download/v0.33.0/geckodriver-v0.33.0-linux64.tar.gz")
    print("   tar -xzf geckodriver-v0.33.0-linux64.tar.gz")
    print("   sudo mv geckodriver /usr/local/bin/")
    print("   sudo chmod +x /usr/local/bin/geckodriver")

def main():
    print("🚀 Agoda Scraper Setup")
    print("=" * 50)
    
    # Check if requirements.txt exists
    if not Path("requirements.txt").exists():
        print("❌ requirements.txt not found!")
        return
    
    # Install requirements
    if not install_requirements():
        return
    
    # Check Firefox
    firefox_ok = check_firefox()
    
    # Geckodriver instructions
    setup_geckodriver()
    
    print("\n" + "=" * 50)
    print("🎯 Setup Complete!")
    print("\n📋 To run the scraper:")
    print("   python agoda_scraper_optimized.py")
    print("\n📊 Output files:")
    print("   - agoda_hotels_final_YYYYMMDD_HHMMSS.csv (main results)")
    print("   - agoda_batch_X_YYYYMMDD_HHMMSS.csv (batch results)")
    print("   - agoda_raw_data_YYYYMMDD_HHMMSS.json (backup)")
    print("   - agoda_scraper.log (logs)")
    
    print("\n⚙️  Configuration:")
    print("   - Edit max_hotels in main() to limit number of hotels")
    print("   - Edit max_workers to change concurrency (default: 5)")
    print("   - Logs are saved to agoda_scraper.log")
    
    if not firefox_ok:
        print("\n⚠️  WARNING: Please install Firefox and geckodriver before running!")

if __name__ == "__main__":
    main()