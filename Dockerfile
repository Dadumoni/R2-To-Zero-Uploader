FROM python:3.11-slim-bookworm

# Prevent python from buffering stdout/stderr and configure default Koyeb port
ENV PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive \
    PORT=8000

# Install ffmpeg, curl, and ca-certificates (Debian 12 Bookworm)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy dependency definition
COPY requirements.txt .

# Install python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright Chromium browser binary and its exact required OS dependencies
RUN playwright install --with-deps chromium

# Copy application source code
COPY . .

# Expose port (Koyeb default: 8000)
EXPOSE 8000

# Run main processor
CMD ["python", "main.py"]
