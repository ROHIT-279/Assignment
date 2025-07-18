#!/usr/bin/env python3
"""
Improved Agoda Scraper Setup and Runner
This script handles virtual environments and modern Python packaging
"""

import subprocess
import sys
import os
import venv
from pathlib import Path

def create_virtual_environment():
    """Create a virtual environment"""
    venv_path = Path("venv")
    if venv_path.exists():
        print("✅ Virtual environment already exists!")
        return True
    
    try:
        print("🔄 Creating virtual environment...")
        venv.create("venv", with_pip=True)
        print("✅ Virtual environment created successfully!")
        return True
    except Exception as e:
        print(f"❌ Error creating virtual environment: {e}")
        return False

def get_venv_python():
    """Get the path to the virtual environment Python executable"""
    if os.name == 'nt':  # Windows
        return Path("venv/Scripts/python.exe")
    else:  # Unix/Linux/macOS
        return Path("venv/bin/python")

def get_venv_pip():
    """Get the path to the virtual environment pip executable"""
    if os.name == 'nt':  # Windows
        return Path("venv/Scripts/pip")
    else:  # Unix/Linux/macOS
        return Path("venv/bin/pip")

def install_requirements_venv():
    """Install required packages in virtual environment"""
    print("📦 Installing required packages in virtual environment...")
    
    venv_pip = get_venv_pip()
    if not venv_pip.exists():
        print(f"❌ Virtual environment pip not found at {venv_pip}")
        return False
    
    try:
        # Upgrade pip first
        subprocess.check_call([str(venv_pip), "install", "--upgrade", "pip"])
        
        # Install requirements
        subprocess.check_call([str(venv_pip), "install", "-r", "requirements.txt"])
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
            print_firefox_install_instructions()
            return False
    except Exception as e:
        print(f"❌ Error checking Firefox: {e}")
        return False

def print_firefox_install_instructions():
    """Print Firefox installation instructions"""
    print("\n🦊 Firefox Installation:")
    print("   Ubuntu/Debian: sudo apt-get install firefox")
    print("   CentOS/RHEL: sudo yum install firefox")
    print("   Fedora: sudo dnf install firefox")
    print("   macOS: brew install --cask firefox")
    print("   Or download from: https://www.mozilla.org/firefox/")

def check_geckodriver():
    """Check if geckodriver is available"""
    print("🔍 Checking for geckodriver...")
    try:
        if os.system("which geckodriver > /dev/null 2>&1") == 0:
            print("✅ Geckodriver found!")
            return True
        else:
            print("❌ Geckodriver not found.")
            print_geckodriver_instructions()
            return False
    except Exception as e:
        print(f"❌ Error checking geckodriver: {e}")
        return False

def print_geckodriver_instructions():
    """Print geckodriver installation instructions"""
    print("\n🔧 Geckodriver Installation:")
    print("   Option 1 - Download and install manually:")
    print("   1. Download from: https://github.com/mozilla/geckodriver/releases")
    print("   2. Extract and move to /usr/local/bin/")
    print("   3. Make executable: chmod +x /usr/local/bin/geckodriver")
    print("")
    print("   Option 2 - Quick Linux install:")
    print("   wget https://github.com/mozilla/geckodriver/releases/download/v0.33.0/geckodriver-v0.33.0-linux64.tar.gz")
    print("   tar -xzf geckodriver-v0.33.0-linux64.tar.gz")
    print("   sudo mv geckodriver /usr/local/bin/")
    print("   sudo chmod +x /usr/local/bin/geckodriver")
    print("")
    print("   Option 3 - macOS with Homebrew:")
    print("   brew install geckodriver")

def create_run_script():
    """Create a script to run the scraper with the virtual environment"""
    venv_python = get_venv_python()
    
    run_script_content = f"""#!/bin/bash
# Agoda Scraper Runner Script
# This script activates the virtual environment and runs the scraper

echo "🚀 Starting Agoda Scraper..."
echo "Using Python: {venv_python}"

# Run the scraper
{venv_python} agoda_scraper_optimized.py

echo "✅ Scraper completed!"
"""
    
    with open("run_scraper.sh", "w") as f:
        f.write(run_script_content)
    
    # Make executable
    os.chmod("run_scraper.sh", 0o755)
    print("✅ Created run_scraper.sh")

def main():
    print("🚀 Improved Agoda Scraper Setup")
    print("=" * 60)
    
    # Check if requirements.txt exists
    if not Path("requirements.txt").exists():
        print("❌ requirements.txt not found!")
        return
    
    # Step 1: Create virtual environment
    if not create_virtual_environment():
        return
    
    # Step 2: Install requirements in virtual environment
    if not install_requirements_venv():
        return
    
    # Step 3: Check Firefox
    firefox_ok = check_firefox()
    
    # Step 4: Check geckodriver
    geckodriver_ok = check_geckodriver()
    
    # Step 5: Create run script
    create_run_script()
    
    print("\n" + "=" * 60)
    print("🎯 Setup Complete!")
    
    print("\n📋 To run the scraper:")
    print("   Option 1: ./run_scraper.sh")
    print("   Option 2: venv/bin/python agoda_scraper_optimized.py")
    print("   Option 3: source venv/bin/activate && python agoda_scraper_optimized.py")
    
    print("\n📊 Expected output files:")
    print("   - agoda_hotels_final_YYYYMMDD_HHMMSS.csv (main results)")
    print("   - agoda_batch_X_YYYYMMDD_HHMMSS.csv (batch results)")
    print("   - agoda_raw_data_YYYYMMDD_HHMMSS.json (backup)")
    print("   - agoda_scraper.log (execution logs)")
    
    print("\n⚙️  Configuration (edit agoda_scraper_optimized.py):")
    print("   - max_hotels: Limit number of hotels to process")
    print("   - max_workers: Number of parallel threads (default: 5)")
    print("   - search_url: Your Agoda search results URL")
    
    print("\n🔧 Virtual Environment:")
    print(f"   - Location: {Path('venv').absolute()}")
    print(f"   - Python: {get_venv_python().absolute()}")
    print(f"   - Pip: {get_venv_pip().absolute()}")
    
    if not firefox_ok or not geckodriver_ok:
        print("\n⚠️  WARNING: Missing dependencies!")
        if not firefox_ok:
            print("   - Please install Firefox browser")
        if not geckodriver_ok:
            print("   - Please install geckodriver")
        print("   Run this script again after installing missing components.")
    else:
        print("\n🎉 All dependencies satisfied! Ready to scrape!")
    
    print("\n💡 Tips:")
    print("   - Start with a small test: edit max_hotels=10 in the script")
    print("   - Monitor progress: tail -f agoda_scraper.log")
    print("   - For issues, check the troubleshooting section in README.md")

if __name__ == "__main__":
    main()