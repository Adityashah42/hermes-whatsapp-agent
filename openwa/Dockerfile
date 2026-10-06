# ==============================================================================
# OpenWA WhatsApp Engine Container (Node 22 Bookworm LTS + Chromium)
# ==============================================================================
FROM node:22-bookworm-slim

# Install system dependencies and Chromium
RUN apt-get update && apt-get install -y --no-install-recommends \
    chromium \
    fonts-liberation \
    ca-certificates \
    curl \
    dumb-init \
    procps \
    && rm -rf /var/lib/apt/lists/*

ENV CHROME_BIN=/usr/bin/chromium
ENV PUPPETEER_SKIP_CHROMIUM_DOWNLOAD=true
ENV PUPPETEER_EXECUTABLE_PATH=/usr/bin/chromium
ENV WA_EXECUTABLE_PATH=/usr/bin/chromium
ENV PUPPETEER_ARGS="--no-sandbox,--disable-setuid-sandbox,--disable-dev-shm-usage,--disable-gpu"

WORKDIR /app

# Install dependencies
COPY openwa/package.json /app/package.json
RUN npm install --omit=dev

RUN mkdir -p /app/data /app/config

COPY openwa/server.js /app/server.js
COPY openwa/config/wa.config.json /app/config/wa.config.json
COPY openwa/entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

ENV PORT=2785
ENV OPENWA_PORT=2785
ENV OPENWA_DATA_PATH=/app/data

EXPOSE 2785

ENTRYPOINT ["/usr/bin/dumb-init", "--", "/app/entrypoint.sh"]
