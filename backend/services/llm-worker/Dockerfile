FROM python:3.11-slim

WORKDIR /app

# Copy requirements first (for Docker layer caching)
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY worker_native.py .

# Run the native async worker for true streaming
CMD ["python", "-u", "worker_native.py"]
