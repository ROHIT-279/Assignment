#!/usr/bin/env python3
"""
Agoda Scraper Configuration Tool
Easily configure the scraper for different requirements
"""

import os
import json
from datetime import datetime

class ScraperConfig:
    def __init__(self):
        self.config_file = "scraper_config.json"
        self.load_config()
    
    def load_config(self):
        """Load existing configuration or create default"""
        default_config = {
            "max_hotels": 25,
            "max_workers": 5,
            "search_url": "https://www.agoda.com/en-in/search?guid=ac34b805-fbbb-4a54-91f6-72bd44251297&asq=oSBZUdCJkTqIcAJrG1AX8Jufa9Vwpz6XltTHq4n%2B9gNpSLc%2BT%2BpB%2F8FnmmA8sOyAJ0WZY5hpLWEr%2Fk8qr78gW4DMS7e7llLtqq76yKsoLJ2OoQ3gw8ln%2FUAwfEcSpHO4IoT8r2EKxXsqX%2FNiA5fxsgqQMycviD3CIWSJVwpQ8sqLB7kVtS1F64bq7yiJpY541pwsBzifP5NpR6wrJ1u54kHb%2BKC2e3zym6tmyvlzCzM%3D&city=10863&tick=638881978745&locale=en-in&ckuid=0782016a-40d3-4e7a-86a4-8cab9dacec41&prid=0&gclid=Cj0KCQjw-NfDBhDyARIsAD-ILeBXva5TJhq-jGK3Si0BOfvtLo82iIstmv4-XMoqfU56Mshxz_UezUkaAhwMEALw_wcB&currency=INR&correlationId=55168ae7-8bc1-4224-a8eb-86ba246be729&analyticsSessionId=-1950121884218971931&pageTypeId=1&realLanguageId=15&languageId=1&origin=IN&stateCode=WB&cid=1922885&tag=6f147157-60b8-459f-af1a-9935d44970e9&userId=0782016a-40d3-4e7a-86a4-8cab9dacec41&whitelabelid=1&loginLvl=0&storefrontId=3&currencyId=27&currencyCode=INR&htmlLanguage=en-in&cultureInfoName=en-in&machineName=sg-pc-6h-acm-web-user-8697c4cd7c-gmgqx&trafficGroupId=5&trafficSubGroupId=122&aid=82361&useFullPageLogin=true&cttp=4&isRealUser=true&mode=production&browserFamily=Chrome&cdnDomain=agoda.net&checkIn=2025-08-12&checkOut=2025-08-13&rooms=1&adults=2&children=0&priceCur=INR&los=1&textToSearch=Darjeeling&travellerType=1&familyMode=off&ds=cgN73pCK5wrspJ7h&productType=-1",
            "headless": True,
            "batch_size": 5,
            "last_updated": datetime.now().isoformat()
        }
        
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    self.config = json.load(f)
                # Merge with defaults for any missing keys
                for key, value in default_config.items():
                    if key not in self.config:
                        self.config[key] = value
            except:
                self.config = default_config
        else:
            self.config = default_config
    
    def save_config(self):
        """Save current configuration"""
        self.config["last_updated"] = datetime.now().isoformat()
        with open(self.config_file, 'w') as f:
            json.dump(self.config, f, indent=2)
        print(f"✅ Configuration saved to {self.config_file}")
    
    def display_current_config(self):
        """Display current configuration"""
        print("\n" + "="*60)
        print("📋 CURRENT SCRAPER CONFIGURATION")
        print("="*60)
        print(f"🏨 Max Hotels to Process: {self.config['max_hotels']}")
        print(f"⚡ Parallel Workers: {self.config['max_workers']}")
        print(f"📦 Batch Size: {self.config['batch_size']}")
        print(f"👁️  Headless Mode: {self.config['headless']}")
        print(f"🌐 Search URL: {self.config['search_url'][:80]}...")
        print(f"📅 Last Updated: {self.config['last_updated']}")
        print("="*60)
    
    def quick_configurations(self):
        """Pre-defined quick configurations"""
        configurations = {
            "1": {
                "name": "🧪 Test Mode (Small)",
                "max_hotels": 10,
                "max_workers": 3,
                "description": "Perfect for testing - 10 hotels, 3 workers"
            },
            "2": {
                "name": "⚡ Fast Mode (Medium)",
                "max_hotels": 50,
                "max_workers": 5,
                "description": "Balanced performance - 50 hotels, 5 workers"
            },
            "3": {
                "name": "🚀 Production Mode (Large)",
                "max_hotels": 200,
                "max_workers": 8,
                "description": "High performance - 200 hotels, 8 workers"
            },
            "4": {
                "name": "🌟 Enterprise Mode (Extra Large)",
                "max_hotels": 1000,
                "max_workers": 10,
                "description": "Maximum scale - 1000 hotels, 10 workers"
            }
        }
        
        print("\n📋 QUICK CONFIGURATION OPTIONS:")
        print("-" * 50)
        for key, config in configurations.items():
            print(f"{key}. {config['name']}")
            print(f"   {config['description']}")
            print()
        
        choice = input("Select configuration (1-4) or press Enter to skip: ").strip()
        
        if choice in configurations:
            selected = configurations[choice]
            self.config['max_hotels'] = selected['max_hotels']
            self.config['max_workers'] = selected['max_workers']
            print(f"✅ Applied {selected['name']}")
            return True
        return False
    
    def interactive_config(self):
        """Interactive configuration"""
        print("\n🔧 INTERACTIVE CONFIGURATION")
        print("-" * 40)
        
        # Max hotels
        current_hotels = self.config['max_hotels']
        hotels_input = input(f"🏨 Max hotels to process [{current_hotels}]: ").strip()
        if hotels_input:
            try:
                self.config['max_hotels'] = int(hotels_input)
            except ValueError:
                print("❌ Invalid number, keeping current value")
        
        # Max workers
        current_workers = self.config['max_workers']
        workers_input = input(f"⚡ Number of parallel workers [{current_workers}]: ").strip()
        if workers_input:
            try:
                self.config['max_workers'] = int(workers_input)
            except ValueError:
                print("❌ Invalid number, keeping current value")
        
        # Headless mode
        current_headless = self.config['headless']
        headless_input = input(f"👁️  Run in headless mode (y/n) [{current_headless}]: ").strip().lower()
        if headless_input in ['y', 'yes', 'n', 'no']:
            self.config['headless'] = headless_input in ['y', 'yes']
        
        # Search URL
        print(f"\n🌐 Current search URL: {self.config['search_url'][:100]}...")
        url_change = input("Update search URL? (y/n): ").strip().lower()
        if url_change in ['y', 'yes']:
            new_url = input("Enter new Agoda search URL: ").strip()
            if new_url:
                self.config['search_url'] = new_url
    
    def generate_run_command(self):
        """Generate command to run with current configuration"""
        return f"python agoda_scraper_optimized.py --max_hotels {self.config['max_hotels']} --max_workers {self.config['max_workers']}"
    
    def estimate_performance(self):
        """Estimate performance with current settings"""
        hotels = self.config['max_hotels']
        workers = self.config['max_workers']
        
        # Based on test results: ~18 seconds per hotel with parallel processing
        time_per_hotel = 18 / workers  # Parallel processing efficiency
        total_minutes = (hotels * time_per_hotel) / 60
        
        print(f"\n📊 PERFORMANCE ESTIMATION:")
        print(f"🏨 Hotels: {hotels}")
        print(f"⚡ Workers: {workers}")
        print(f"⏱️  Estimated Time: {total_minutes:.1f} minutes")
        print(f"📈 Hotels/Hour: {int(60 * hotels / total_minutes)}")
    
    def main_menu(self):
        """Main configuration menu"""
        while True:
            self.display_current_config()
            self.estimate_performance()
            
            print("\n🔧 CONFIGURATION OPTIONS:")
            print("1. Quick Configuration Presets")
            print("2. Interactive Configuration")
            print("3. Update Search URL Only")
            print("4. Reset to Defaults")
            print("5. Save & Exit")
            print("6. Exit Without Saving")
            
            choice = input("\nSelect option (1-6): ").strip()
            
            if choice == "1":
                if self.quick_configurations():
                    print("✅ Configuration updated!")
            
            elif choice == "2":
                self.interactive_config()
                print("✅ Configuration updated!")
            
            elif choice == "3":
                new_url = input("Enter new Agoda search URL: ").strip()
                if new_url:
                    self.config['search_url'] = new_url
                    print("✅ Search URL updated!")
            
            elif choice == "4":
                confirm = input("⚠️  Reset to defaults? (y/n): ").strip().lower()
                if confirm in ['y', 'yes']:
                    self.load_config()  # This will load defaults if file doesn't exist
                    self.config = {
                        "max_hotels": 25,
                        "max_workers": 5,
                        "headless": True,
                        "batch_size": 5,
                        "search_url": self.config['search_url'],  # Keep current URL
                        "last_updated": datetime.now().isoformat()
                    }
                    print("✅ Reset to defaults!")
            
            elif choice == "5":
                self.save_config()
                print("\n🚀 To run scraper with these settings:")
                print(f"   ./run_scraper.sh")
                print(f"   (or manually edit agoda_scraper_optimized.py)")
                break
            
            elif choice == "6":
                print("👋 Exiting without saving...")
                break
            
            else:
                print("❌ Invalid option, please try again")

if __name__ == "__main__":
    print("🔧 Agoda Scraper Configuration Tool")
    print("=" * 50)
    
    config = ScraperConfig()
    config.main_menu()