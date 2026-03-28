FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Create config if not exists
RUN cp config/.env.example config/.env 2>/dev/null || true

EXPOSE 8876 8877

CMD ["python", "src/main.py"]
