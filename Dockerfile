FROM python:3.11-slim

LABEL org.opencontainers.image.title="gracenote2xmltv" \
      org.opencontainers.image.description="Convert Gracenote/Zap2it TV listings to XMLTV format and serve via HTTP" \
      org.opencontainers.image.source="https://github.com/AndyG-0/tvtv2xmltv"

# Set working directory
WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy project files
COPY pyproject.toml .
COPY src/ ./src/
COPY tests/fixtures/ ./tests/fixtures/

# Install dependencies using uv (without the package itself)
RUN uv pip install --system --no-cache requests flask python-dateutil pytz

# Create directory for output files
RUN mkdir -p /data

# Expose port
EXPOSE 8080

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV GRACENOTE_OUTPUT_FILE=/data/xmltv.xml
ENV TVTV_OUTPUT_FILE=/data/xmltv.xml
ENV GRACENOTE_TIMEZONE=America/Phoenix
ENV TVTV_TIMEZONE=America/Phoenix
ENV GRACENOTE_LINEUPS=85142_OTA
ENV TVTV_LINEUPS=85142_OTA
ENV PYTHONPATH=/app/src

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')" || exit 1

# Run the application
CMD ["python", "src/main.py", "--mode", "serve"]
