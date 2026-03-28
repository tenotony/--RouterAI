FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source
COPY . .

EXPOSE 8900 8899

CMD ["python", "src/proxy.py", "--host", "0.0.0.0", "--port", "8900"]
