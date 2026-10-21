FROM python:3.10-slim-bullseye

# Prevent python from buffering stdout/stderr
ENV PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive \
    PORT=8080

# Install system dependencies including ffmpeg and required libraries for Chromium
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    ca-certificates \
    libnss3 \
    libatk-bridge2.0-0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy dependency definition
COPY requirements.txt .

# Install python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright Chromium browser binary and its OS dependencies
RUN playwright install --with-deps chromium

# Copy application source code
COPY . .

# Expose port (Railway will bind to $PORT)
EXPOSE 8080

# Run main processor
CMD ["python", "main.py"]
