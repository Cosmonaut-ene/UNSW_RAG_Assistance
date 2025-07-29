#!/usr/bin/env python3
"""
Full Scraping Pipeline Script

Runs the complete workflow: discovery → scraping → vector store update
"""

import sys
import os
import argparse
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scrapers.link_discovery import discover_and_save_cse_links
from scrapers.monitor import get_new_links, get_scraping_status, update_scraping_metadata
from scrapers.page_scraper import scrape_urls_batch
from scrapers.config import config
from rag import update_knowledge_base, get_content_sources_summary

def run_discovery(browse_url):
    """Step 1: Discover links"""
    print("🔍 STEP 1: Link Discovery")
    print("-" * 30)
    
    links = discover_and_save_cse_links(browse_url)
    total = sum(len(v) for v in links.values())
    
    print(f"✅ Discovered {total} links")
    print(f"   Programs: {len(links.get('programs', []))}")
    print(f"   Specialisations: {len(links.get('specialisations', []))}")
    print(f"   Courses: {len(links.get('courses', []))}")
    
    return total

def run_scraping(max_urls=None):
    """Step 2: Scrape content"""
    print("\n📄 STEP 2: Content Scraping")
    print("-" * 30)
    
    # Get URLs that need scraping
    new_urls = get_new_links()
    
    if not new_urls:
        print("✅ No new URLs to scrape")
        return 0
    
    if max_urls and len(new_urls) > max_urls:
        print(f"📋 Limiting to {max_urls} URLs (out of {len(new_urls)})")
        new_urls = new_urls[:max_urls]
    
    # Scrape URLs
    print(f"🚀 Scraping {len(new_urls)} URLs...")
    documents = scrape_urls_batch(new_urls, headless=True, save_content=True)
    
    # Get successful URLs
    successful_urls = [doc.metadata["source"] for doc in documents]
    
    # Update metadata
    update_scraping_metadata(successful_urls)
    
    print(f"✅ Scraped {len(successful_urls)}/{len(new_urls)} URLs successfully")
    
    return len(successful_urls)

def run_vector_update():
    """Step 3: Update vector store"""
    print("\n🗂️  STEP 3: Vector Store Update")
    print("-" * 30)
    
    # Get content summary
    summary = get_content_sources_summary()
    
    print(f"📊 Content sources:")
    print(f"   PDF files: {summary['pdf_sources']['count']}")
    print(f"   Scraped content: {summary['scraped_sources']['count']}")
    print(f"   Total: {summary['total_sources']}")
    
    if summary['total_sources'] == 0:
        print("⚠️  No content to process")
        return False
    
    # Update vector store
    print("🚀 Updating vector store...")
    update_vector_store_with_scraped()
    
    print("✅ Vector store updated successfully")
    return True

def main():
    """Run the complete pipeline"""
    parser = argparse.ArgumentParser(description="UNSW CSE Scraping Pipeline")
    parser.add_argument("--skip-discovery", action="store_true", help="Skip link discovery step")
    parser.add_argument("--skip-scraping", action="store_true", help="Skip content scraping step")
    parser.add_argument("--skip-vector-update", action="store_true", help="Skip vector store update")
    parser.add_argument("--max-urls", type=int, help="Maximum URLs to scrape")
    parser.add_argument("--browse-url", default="https://www.handbook.unsw.edu.au/browse/By%20Area%20of%20Interest/InformationTechnology", 
                       help="Browse page URL for discovery")
    
    args = parser.parse_args()
    
    print("🎯 UNSW CSE Scraping Pipeline")
    print("=" * 50)
    
    # Ensure directories exist
    config.ensure_directories()
    
    try:
        # Step 1: Discovery
        if not args.skip_discovery:
            links_count = run_discovery(args.browse_url)
        else:
            print("⏭️  Skipping link discovery")
        
        # Step 2: Scraping
        if not args.skip_scraping:
            scraped_count = run_scraping(args.max_urls)
        else:
            print("⏭️  Skipping content scraping")
            scraped_count = 0
        
        # Step 3: Vector Store Update
        if not args.skip_vector_update:
            vector_updated = run_vector_update()
        else:
            print("⏭️  Skipping vector store update")
            vector_updated = False
        
        # Final summary
        print("\n🎉 PIPELINE COMPLETED")
        print("=" * 50)
        
        final_status = get_scraping_status()
        final_summary = get_content_sources_summary()
        
        print(f"📊 Final Status:")
        print(f"   Total URLs in file: {final_status['total_urls']}")
        print(f"   Successfully scraped: {final_status['scraped_count']}")
        print(f"   Completion rate: {final_status['completion_rate']:.1f}%")
        print(f"   Vector store sources: {final_summary['total_sources']}")
        print(f"   Vector store exists: {final_summary['vector_store_exists']}")
        
        if final_summary['vector_store_exists']:
            print(f"\n✅ The RAG chatbot is ready to answer questions!")
        else:
            print(f"\n⚠️  Vector store not ready. Check the logs for errors.")
        
    except Exception as e:
        print(f"\n❌ Pipeline failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()