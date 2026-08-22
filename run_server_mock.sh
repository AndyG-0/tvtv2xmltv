#!/bin/bash
# Test script to run the server in mock mode with 85142 lineups
# This avoids hitting the real API during development/testing

export GRACENOTE_TIMEZONE=America/Phoenix
export GRACENOTE_LINEUPS=85142_OTA,85142_AZ02490
export GRACENOTE_DAYS=1
export GRACENOTE_PORT=8081
export GRACENOTE_MOCK_MODE=true

# Backward-compatible TVTV_* exports
export TVTV_TIMEZONE=America/Phoenix
export TVTV_LINEUPS=85142_OTA,85142_AZ02490
export TVTV_DAYS=1
export TVTV_PORT=8081
export TVTV_MOCK_MODE=true

echo "Starting server in MOCK MODE for 85142 (America/Phoenix)..."
echo "Lineups: $GRACENOTE_LINEUPS"
echo "Port: $GRACENOTE_PORT"
echo ""

uv run python src/main.py --mode serve
