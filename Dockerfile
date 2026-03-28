FROM python:3.12-slim

WORKDIR /app

# Install system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies first (cache layer)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source
COPY . .

# Create default api_keys.json if not exists
RUN echo '{}' > /app/api_keys.json

# Expose ports
EXPOSE 8900 8899

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://127.0.0.1:8900/api/status || exit 1

# Default: run proxy. Override in docker-compose for dashboard.
CMD ["python", "src/proxy.py", "--host", "0.0.0.0", "--port", "8900"]
