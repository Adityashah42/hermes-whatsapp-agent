# ==============================================================================
# OpenWA WhatsApp Engine Container
# ==============================================================================
FROM openwa/wa-automate:latest

USER root

# Create app directory
RUN mkdir -p /app/config /app/data

COPY openwa/config/wa.config.json /app/config/wa.config.json
COPY openwa/entrypoint.sh /app/entrypoint.sh

RUN chmod +x /app/entrypoint.sh

ENV OPENWA_PORT=2785
ENV OPENWA_DATA_PATH=/app/data
ENV PORT=2785

EXPOSE 2785

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:2785/ || exit 1

ENTRYPOINT ["/app/entrypoint.sh"]
