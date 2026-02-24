#!/bin/bash
# Ensure data directories exist and are writable
mkdir -p /data/knowledge_base/vector_store \
         /data/knowledge_base/documents \
         /data/knowledge_base/scraped_content/content \
         /data/knowledge_base/logs

exec python app.py
