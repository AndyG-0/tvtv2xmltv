#!/bin/bash
# Test script to run the server in mock mode with your lineups
# This avoids hitting the real API during development/testing

export TVTV_TIMEZONE=America/Phoenix
export TVTV_LINEUPS=luUSA-OTA85142,luUSA-AZ02490-X
export TVTV_DAYS=1
export TVTV_PORT=8081
export TVTV_MOCK_MODE=true

echo "Starting server in MOCK MODE..."
echo "Lineups: $TVTV_LINEUPS"
echo "Port: $TVTV_PORT"
echo ""

uv run python src/main.py --mode serve
