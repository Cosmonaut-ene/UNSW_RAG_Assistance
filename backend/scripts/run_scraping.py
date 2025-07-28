#!/usr/bin/env python3
"""
Content Scraping Script

Scrapes content from URLs in urls.txt and saves to content directory
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scrapers.services.monitoring_service import get_new_links, update_scraping_metadata
from scrapers.services.scraping_service import scrape_urls_batch
from scrapers.config import config

def main():
    """Run content scraping"""
    print("📄 UNSW CSE Content Scraping")
    print("=" * 50)
    
    # Ensure directories exist
    config.ensure_directories()
    
    try:
        # Get URLs that need scraping
        new_urls = get_new_links()
        
        if not new_urls:
            print("✅ No new URLs to scrape. All content is up to date.")
            return
        
        print(f"📋 Found {len(new_urls)} URLs to scrape")
        
        # Ask for confirmation if many URLs
        if len(new_urls) > 10:
            print(f"\n⚠️  This will scrape {len(new_urls)} URLs which may take a while.")
            response = input("Continue? (y/N): ").lower().strip()
            if response != 'y':
                print("Cancelled.")
                return
        
        # Scrape URLs
        print(f"\n🚀 Starting content scraping...")
        documents = scrape_urls_batch(new_urls, save_content=True)
        
        # Get successful URLs
        successful_urls = [doc.metadata["source"] for doc in documents]
        
        # Update metadata
        update_scraping_metadata(successful_urls)
        
        print(f"\n✅ Scraping completed!")
        print(f"📊 Results:")
        print(f"   Total URLs: {len(new_urls)}")
        print(f"   Successful: {len(successful_urls)}")
        print(f"   Failed: {len(new_urls) - len(successful_urls)}")
        print(f"\n💾 Content saved to: {config.CONTENT_DIR}")
        
        if successful_urls:
            print(f"\n💡 Next step: Run vector store update")
            print(f"   python scripts/update_vector_store.py")
        
    except Exception as e:
        print(f"❌ Scraping failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()