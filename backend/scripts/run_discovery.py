#!/usr/bin/env python3
"""
Link Discovery Script

Discovers CSE links from UNSW handbook browse page and saves to urls.txt
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scrapers.services.discovery_service import discover_and_save_cse_links
from scrapers.config import config

def main():
    """Run link discovery"""
    print("🔍 UNSW CSE Link Discovery")
    print("=" * 50)
    
    # Ensure directories exist
    config.ensure_directories()
    
    # Default browse URL
    browse_url = "https://www.handbook.unsw.edu.au/browse/By%20Area%20of%20Interest/InformationTechnology"
    
    try:
        print(f"Discovering links from: {browse_url}")
        links = discover_and_save_cse_links(browse_url)
        
        total = sum(len(v) for v in links.values())
        print(f"\n✅ Discovery completed successfully!")
        print(f"📊 Results:")
        print(f"   Programs: {len(links.get('programs', []))}")
        print(f"   Double Degrees: {len(links.get('double_degrees', []))}")
        print(f"   Specialisations: {len(links.get('specialisations', []))}")
        print(f"   Courses: {len(links.get('courses', []))}")
        print(f"   Total: {total}")
        print(f"\n💾 Links saved to: {config.URLS_FILE}")
        
    except Exception as e:
        print(f"❌ Discovery failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()