# tvtv2xmltv

Convert TV listings from [tvtv.us](https://www.tvtv.us/) to XMLTV format and serve them via HTTP.

## Features

- ✅ Fetches TV guide data from tvtv.us API
- ✅ Converts to standard XMLTV format
- ✅ Built-in HTTP server to serve XMLTV files
- ✅ Automatic periodic updates
- ✅ Docker support with docker-compose
- ✅ Configurable via environment variables
- ✅ Health check endpoints
- ✅ Comprehensive test coverage
- ✅ CI/CD with GitHub Actions

## Quick Start with Docker or Podman

The easiest way to run tvtv2xmltv is with Docker or Podman:

### Using Docker

```bash
# Clone the repository
git clone https://github.com/AndyG-0/tvtv2xmltv.git
cd tvtv2xmltv

# Copy and edit environment variables
cp .env.example .env
# Edit .env with your lineup ID and preferences

# Start with docker-compose
docker-compose up -d
```

### Using Podman

```bash
# Clone the repository
git clone https://github.com/AndyG-0/tvtv2xmltv.git
cd tvtv2xmltv

# Copy and edit environment variables
cp .env.example .env
# Edit .env with your lineup ID and preferences

# Start with podman-compose
podman-compose up -d
```

The XMLTV file will be available at `http://localhost:8080/xmltv.xml` (or `http://localhost:8081/xmltv.xml` if you set `TVTV_PORT=8081`)

## Configuration

Configure the application using environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `TVTV_TIMEZONE` | Timezone for guide data (see [tz database](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones)) | `America/New_York` |
| `TVTV_LINEUPS` | Comma-separated list of TVTV lineup IDs (e.g., `USA-ONE,USA-TWO`). Each lineup will generate its own XMLTV file. | (optional) |
| `TVTV_LINEUP_ID` | (Deprecated when `TVTV_LINEUPS` is set) Your TVTV lineup ID (find at [tvtv.us](https://www.tvtv.us/)) | `USA-OTA30236` |
| `TVTV_DAYS` | Number of days to fetch (1-8) | `8` |
| `TVTV_UPDATE_INTERVAL` | Update interval in seconds | `3600` |
| `TVTV_PORT` | HTTP server port | `8080` |
| `TVTV_HOST` | HTTP server host | `0.0.0.0` |
| `TVTV_OUTPUT_FILE` | Output file path (used only for single lineup mode) | `xmltv.xml` |
| `TVTV_MOCK_MODE` | Use mock data instead of real API (for testing) | `false` |

### Finding Your Lineup ID

1. Visit [tvtv.us](https://www.tvtv.us/)
2. Enter your location/zip code
3. Select your TV provider
4. The lineup ID will be in the URL (e.g., `USA-OTA30236`)

**Multiple Lineups:** You can specify multiple lineup IDs using the `TVTV_LINEUPS` environment variable with a comma-separated list (e.g., `TVTV_LINEUPS=USA-OTA30236,USA-OTA90210`). Each lineup will generate its own XMLTV file and be accessible at `/<lineup-id>.xml` (e.g., `/USA-OTA30236.xml`, `/USA-OTA90210.xml`).

### Mock Mode for Testing

To test the application without hitting the real API (useful during development):

```bash
export TVTV_MOCK_MODE=true
export TVTV_LINEUPS=luUSA-OTA85142,luUSA-AZ02490-X
./run_server_mock.sh
```

Or use the included mock server script:

```bash
./run_server_mock.sh
```

Mock mode uses fixture data from `tests/fixtures/` directory.

## Installation

### Docker or Podman (Recommended)

**Using Docker:**

```bash
# Build the image
docker build -t tvtv2xmltv .

# Run the container
docker run -d \
  -p 8080:8080 \
  -e TVTV_LINEUPS=YOUR_LINEUP_ID_1,YOUR_LINEUP_ID_2 \
  -e TVTV_TIMEZONE=America/New_York \
  -v tvtv-data:/data \
  tvtv2xmltv

# Or, for backwards compatibility use TVTV_LINEUP_ID (single lineup):
#  -e TVTV_LINEUP_ID=YOUR_LINEUP_ID
```

**Using Podman:**

```bash
# Build the image
podman build -t tvtv2xmltv .

# Run the container
podman run -d \
  -p 8080:8080 \
  -e TVTV_LINEUPS=YOUR_LINEUP_ID_1,YOUR_LINEUP_ID_2 \
  -e TVTV_TIMEZONE=America/New_York \
  -v tvtv-data:/data \
  tvtv2xmltv

# Or use podman-compose
podman-compose -f podman-compose.yml up -d
```

### Python (Manual)

```bash
# Clone the repository
git clone https://github.com/AndyG-0/tvtv2xmltv.git
cd tvtv2xmltv

# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv pip install -e .

# Run the server
export TVTV_LINEUP_ID=YOUR_LINEUP_ID
python src/main.py --mode serve
```

## Usage

### Server Mode (Default)

Run as an HTTP server that automatically updates the XMLTV file:

```bash
python src/main.py --mode serve
```

Access the XMLTV file at:
- `http://localhost:8080/` or `http://localhost:8080/xmltv.xml` - Download XMLTV file
- `http://localhost:8080/health` - Health check endpoint
- `http://localhost:8080/update` - Manually trigger update

### Convert Mode

Generate XMLTV file once and exit:

```bash
python src/main.py --mode convert --output guide.xml
```

## Integration with Media Servers

### Jellyfin

1. Install the XMLTV plugin in Jellyfin
2. Configure the XMLTV plugin:
   - **Single lineup:** `http://your-server:8080/xmltv.xml`
   - **Multiple lineups:** `http://your-server:8080/<lineup-id>.xml` (e.g., `http://your-server:8080/USA-OTA30236.xml`)
3. Set up automatic refresh (recommended: every 12-24 hours)

### Plex

1. Configure Plex DVR settings
2. Add XMLTV source:
   - **Single lineup:** `http://your-server:8080/xmltv.xml`
   - **Multiple lineups:** `http://your-server:8080/<lineup-id>.xml`

### Emby

1. Go to Live TV settings
2. Add guide data provider
3. Use URL:
   - **Single lineup:** `http://your-server:8080/xmltv.xml`
   - **Multiple lineups:** `http://your-server:8080/<lineup-id>.xml`

## Development

### Setup

```bash
# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install development dependencies
uv pip install -e ".[dev]"

# Run tests
uv run pytest tests/ -v

# Run with coverage
uv run pytest tests/ --cov=tvtv2xmltv --cov-report=html

# Lint code
uv run flake8 src/

# Format code
uv run black src/
```

### Running Tests

```bash
# All tests
uv run pytest tests/ -v

# Specific test file
uv run pytest tests/test_config.py -v

# With coverage
uv run pytest tests/ --cov=tvtv2xmltv --cov-report=term --cov-report=html
```

### Project Structure

```
tvtv2xmltv/
├── src/
│   ├── main.py                    # Entry point
│   └── tvtv2xmltv/
│       ├── __init__.py
│       ├── config.py              # Configuration management
│       ├── tvtv_client.py         # TVTV API client
│       ├── xmltv_generator.py     # XMLTV format generator
│       ├── converter.py           # Main conversion logic
│       └── server.py              # HTTP server
├── tests/
│   ├── test_config.py
│   ├── test_tvtv_client.py
│   ├── test_xmltv_generator.py
│   ├── test_converter.py
│   └── test_server.py
├── .github/
│   └── workflows/
│       ├── ci.yml                 # CI/CD pipeline
│       └── docker.yml             # Docker build
├── Dockerfile
├── docker-compose.yml
├── podman-compose.yml
├── setup.cfg
├── pyproject.toml
└── README.md
```

## API Endpoints

### Single Lineup Mode
- `GET /` - Download XMLTV file
- `GET /xmltv.xml` - Download XMLTV file (alternative endpoint)
- `GET /health` - Health check (returns JSON with status)
- `GET /update` - Manually trigger XMLTV update

### Multiple Lineup Mode
- `GET /` - List available lineups (HTML page with links)
- `GET /<lineup-id>.xml` - Download XMLTV file for specific lineup (e.g., `/USA-OTA30236.xml`)
- `GET /health` - Health check (returns JSON with status and lineup list)
- `GET /update` - Manually trigger XMLTV update for all lineups

## XMLTV Format

The generated XMLTV file follows the [XMLTV DTD specification](http://wiki.xmltv.org/index.php/XMLTVFormat) and includes:

- Channel information (number, call sign, logo)
- Program details (title, subtitle, description)
- Program metadata (categories, ratings, HD/stereo flags)
- Accurate start/stop times in local timezone

## Troubleshooting

### Connection Issues

If you're getting connection errors:
1. Check your internet connection
2. Verify the lineup ID is correct
3. Check firewall settings

### Empty Guide Data

If the XMLTV file is empty:
1. Verify your lineup ID at tvtv.us
2. Check the logs for error messages
3. Try reducing the number of days

### Docker/Podman Issues

**Using Docker:**

```bash
# View logs
docker-compose logs -f

# Restart service
docker-compose restart

# Rebuild image
docker-compose up -d --build
```

**Using Podman:**

```bash
# View logs
podman-compose logs -f

# Restart service
podman-compose restart

# Rebuild image
podman-compose up -d --build
```

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## License

MIT License - see LICENSE file for details

## Credits

Based on the original PHP implementation by [idolpx](https://gist.github.com/idolpx/c82747bb740c303f56ad8a1e8f17d575)

## Related Projects

- [XMLTV](http://xmltv.org/) - Original XMLTV project
- [tvtv.us](https://www.tvtv.us/) - TV guide data source

## Support

For issues and questions:
- Open an issue on GitHub
- Check existing issues for solutions
- Review the troubleshooting section