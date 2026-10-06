# ==============================================================================
# OpenWA WhatsApp Engine Container (Node 22 Bookworm LTS + Official Google Chrome)
# ==============================================================================
FROM node:22-bookworm-slim

# Install system dependencies and Google Chrome Stable
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    gnupg \
    ca-certificates \
    procps \
    dumb-init \
    libnss3 \
    libatk-bridge2.0-0 \
    libgtk-3-0 \
    libgbm1 \
    libasound2 \
    fonts-liberation \
    xvfb \
    xauth \
    && wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | gpg --dearmor -o /usr/share/keyrings/google-linux-keyring.gpg \
    && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-linux-keyring.gpg] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

ENV CHROME_BIN=/usr/bin/google-chrome-stable
ENV PUPPETEER_SKIP_CHROMIUM_DOWNLOAD=true
ENV PUPPETEER_EXECUTABLE_PATH=/usr/bin/google-chrome-stable
ENV WA_EXECUTABLE_PATH=/usr/bin/google-chrome-stable
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
