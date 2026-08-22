#!/bin/bash
# Quick start script for tvtv2xmltv

set -e

echo "🚀 tvtv2xmltv Quick Start Script"
echo "=================================="
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    echo "   Visit: https://docs.docker.com/get-docker/"
    exit 1
fi

echo "✅ Docker is installed"

# Check if docker-compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "⚠️  docker-compose is not installed. Trying docker compose..."
    if ! docker compose version &> /dev/null; then
        echo "❌ docker-compose is not available. Please install it."
        echo "   Visit: https://docs.docker.com/compose/install/"
        exit 1
    fi
    DOCKER_COMPOSE="docker compose"
else
    DOCKER_COMPOSE="docker-compose"
fi

echo "✅ Docker Compose is available"
echo ""

# Check if .env exists, if not copy from example
if [ ! -f .env ]; then
    echo "📝 Creating .env file from .env.example..."
    cp .env.example .env
    echo "ℹ️  Default lineup is set for 85142 (85142_OTA, America/Phoenix)."
    echo "⚠️  You can edit .env if you wish to adjust GRACENOTE_LINEUPS before running!"
    echo ""
    echo "To find your lineup ID (format: {zipCode}_{headendId}):"
    echo "  - For local broadcast: {yourZip}_OTA (e.g., 85142_OTA)"
    echo "  - For a specific provider, look up its headendId:"
    echo "    curl 'https://tvlistings.gracenote.com/gapzap_webapi/api/Providers/getPostalCodeProviders/USA/{yourZip}/gapzap/en'"
    echo ""
    read -p "Press Enter to review/edit .env file (or Ctrl+C to exit)..."
    ${EDITOR:-nano} .env
fi

echo "🏗️  Building Docker image..."
$DOCKER_COMPOSE build

echo ""
echo "🚀 Starting tvtv2xmltv service..."
$DOCKER_COMPOSE up -d

echo ""
echo "✅ Service started successfully!"
echo ""
echo "📡 The XMLTV file will be available at:"
echo "   http://localhost:8080/xmltv.xml"
echo ""
echo "🏥 Health check endpoint:"
echo "   http://localhost:8080/health"
echo ""
echo "📊 View logs:"
echo "   $DOCKER_COMPOSE logs -f"
echo ""
echo "🛑 Stop service:"
echo "   $DOCKER_COMPOSE down"
echo ""
echo "Happy TV watching! 📺"
