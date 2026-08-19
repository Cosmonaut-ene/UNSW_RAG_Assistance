# Pinned to a specific Debian release, not the floating python:3.12-slim
# tag -- that tag silently moved to a Debian 13 (trixie) base at some
# point, which dropped `apt-key` entirely and broke this build (caught by
# a fresh CI run with no local layer cache to hide it; a locally-cached
# image had masked it here).
FROM python:3.12-slim-bookworm

# Set working directory
WORKDIR /app

# Install system dependencies including Chrome for web scraping
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    wget \
    gnupg \
    unzip \
    && wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | gpg --dearmor -o /usr/share/keyrings/google-chrome.gpg \
    && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-chrome.gpg] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies. torch is a transitive dependency (via
# sentence-transformers) with no version pinned in requirements.txt, and
# PyPI's default torch wheel bundles full CUDA support -- ~6.85GB of
# nvidia-*/torch/triton packages that are pure waste here: embeddings run
# CPU-only (see model_kwargs={"device": "cpu"} in ai/llm_client.py) and
# this deploys to a Hetzner VPS with no GPU at all. Installing the
# CPU-only build first means the later `pip install -r requirements.txt`
# finds it already satisfies sentence-transformers' torch requirement and
# never pulls in the CUDA variant. This single change took the image from
# ~10GB to a size GHCR could actually push without a single 3GB+ layer
# timing out mid-upload (see PR history).
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu
RUN pip install --no-cache-dir -r requirements.txt
RUN python -m spacy download en_core_web_sm

# Copy application code
COPY . .

# Create data directories (they may be overridden by volume mounts)
RUN mkdir -p /data/knowledge_base/vector_store \
             /data/knowledge_base/documents \
             /data/knowledge_base/scraped_content/content \
             /data/knowledge_base/logs

# Set environment variables
ENV PYTHONPATH=/app
ENV FLASK_APP=app.py
ENV FLASK_ENV=production

# Expose port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:5000/api/admin/health || exit 1

# Run as root so bind-mounted volumes are writable on Windows/Mac Docker Desktop
CMD ["python", "app.py"]
