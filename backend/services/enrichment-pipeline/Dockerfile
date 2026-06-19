FROM python:3.11

WORKDIR /app

# Install system dependencies required for Playwright/Chromium
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libc-bin \
    libglib2.0-0 \
    libglib2.0-dev \
    libgobject-2.0-0 \
    libnspr4 \
    libnss3 \
    libdbus-1-3 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libexpat1 \
    libatspi2.0-0 \
    libx11-6 \
    libxcomposite1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libxcb1 \
    libxkbcommon0 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libcups2 \
    libdrm2 \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browser dependencies and Chromium browser
RUN playwright install-deps && playwright install chromium

# Download FinBERT model at build time to cache it
RUN python -c "from transformers import AutoTokenizer, AutoModelForSequenceClassification; \
    AutoTokenizer.from_pretrained('ProsusAI/finbert'); \
    AutoModelForSequenceClassification.from_pretrained('ProsusAI/finbert')"

# Copy application code (all modules)
COPY *.py .

# Expose monitoring port
EXPOSE 8080

# Run the native pipeline for true streaming
CMD ["python", "-u", "pipeline_native.py"]
