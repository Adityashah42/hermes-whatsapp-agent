# ==============================================================================
# OpenWA WhatsApp Engine Container (Node 20 LTS + Chromium)
# ==============================================================================
FROM node:20-bullseye-slim

# Install system dependencies and Chromium for headless automation
RUN apt-get update && apt-get install -y --no-install-recommends \
    chromium \
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libc6 \
    libcairo2 \
    libcups2 \
    libdbus-1-3 \
    libexpat1 \
    libfontconfig1 \
    libgbm1 \
    libgcc1 \
    libglib2.0-0 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libstdc++6 \
    libx11-6 \
    libx11-xcb1 \
    libxcb1 \
    libxcomposite1 \
    libxcursor1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxi6 \
    libxrandr2 \
    libxrender1 \
    libxss1 \
    libxtst6 \
    ca-certificates \
    curl \
    dumb-init \
    && rm -rf /var/lib/apt/lists/*

ENV CHROME_BIN=/usr/bin/chromium
ENV PUPPETEER_SKIP_CHROMIUM_DOWNLOAD=true
ENV PUPPETEER_EXECUTABLE_PATH=/usr/bin/chromium
ENV WA_EXECUTABLE_PATH=/usr/bin/chromium

WORKDIR /app

# Install @open-wa/wa-automate
RUN npm install -g @open-wa/wa-automate

RUN mkdir -p /app/data /app/config

COPY openwa/config/wa.config.json /app/config/wa.config.json
COPY openwa/entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

ENV PORT=2785
ENV OPENWA_PORT=2785
ENV OPENWA_DATA_PATH=/app/data

EXPOSE 2785

ENTRYPOINT ["/usr/bin/dumb-init", "--", "/app/entrypoint.sh"]
