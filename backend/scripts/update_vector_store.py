#!/usr/bin/env python3
"""
Vector Store Update Script

Updates the RAG vector store with PDF files and scraped content
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rag import update_knowledge_base, get_content_sources_summary

def main():
    """Update vector store with all content"""
    print("🗂️  RAG Vector Store Update")
    print("=" * 50)
    
    try:
        # Get current content summary
        print("📊 Checking current content sources...")
        summary = get_content_sources_summary()
        
        print(f"   PDF files: {summary['pdf_sources']['count']}")
        print(f"   Scraped content: {summary['scraped_sources']['count']}")
        print(f"   Total sources: {summary['total_sources']}")
        
        if summary['total_sources'] == 0:
            print("\n⚠️  No content sources found. Run discovery and scraping first.")
            return
        
        print(f"\n🚀 Updating vector store...")
        update_knowledge_base(include_scraped=True)
        
        print(f"\n✅ Vector store update completed!")
        print(f"📈 The RAG system now includes:")
        print(f"   - {summary['pdf_sources']['count']} PDF documents")
        print(f"   - {summary['scraped_sources']['count']} scraped web pages")
        
        print(f"\n💡 The chatbot is now ready to answer questions using the updated knowledge base.")
        
    except Exception as e:
        print(f"❌ Vector store update failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()