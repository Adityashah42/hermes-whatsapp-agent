# ==============================================================================
# Hermes Agent + Antigravity CLI + WhatsApp Router Container
# ==============================================================================
FROM nousresearch/hermes-agent:latest

USER root

# Install system dependencies needed for agy CLI, Python pip, and networking
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    git \
    procps \
    sqlite3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Install official Antigravity CLI (agy)
RUN (curl -fsSL https://antigravity.google/cli/install.sh | bash || true) && \
    if [ -f "/root/.local/bin/agy" ]; then \
        cp /root/.local/bin/agy /usr/local/bin/agy && \
        chmod +x /usr/local/bin/agy; \
    fi

# Create application directories
RUN mkdir -p /opt/hermes/integration /opt/hermes/skills/antigravity-cli /opt/data

# Copy Integration router and dependencies
COPY integration/requirements.txt /opt/hermes/integration/requirements.txt
RUN pip3 install --no-cache-dir --break-system-packages -r /opt/hermes/integration/requirements.txt || \
    pip install --no-cache-dir -r /opt/hermes/integration/requirements.txt

COPY integration/ /opt/hermes/integration/
COPY hermes/skills/antigravity-cli/ /opt/hermes/skills/antigravity-cli/
COPY hermes/entrypoint.sh /opt/hermes/entrypoint.sh

RUN chmod +x /opt/hermes/entrypoint.sh

# Environment defaults
ENV PYTHONUNBUFFERED=1
ENV PORT=8080
ENV HERMES_API_PORT=8642
ENV HERMES_DATA_PATH=/opt/data
ENV PATH="/usr/local/bin:/root/.local/bin:${PATH}"

# Ports: 8080 (Integration Router & Health check), 8642 (Hermes API Server)
EXPOSE 8080 8642

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

ENTRYPOINT ["/bin/bash", "/opt/hermes/entrypoint.sh"]
