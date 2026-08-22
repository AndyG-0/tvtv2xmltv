# tvtv2xmltv

Convert TV listings to XMLTV format and serve them via HTTP.

## Features

- ✅ Fetches TV guide data from the free Gracenote/Zap2it grid API (up to 14 days)
- ✅ Converts to standard XMLTV format
- ✅ Comprehensive feed statistics reporting (channels retrieved, days of guide, date coverage, total programs, file size, and last refreshed timestamp)
- ✅ Interactive web dashboard (`/list` or `/dashboard`) with on-demand feed **Reload** button
- ✅ Built-in HTTP server to serve XMLTV files
- ✅ Automatic periodic updates
- ✅ Docker support with docker-compose
- ✅ Configurable via environment variables
- ✅ Health check and feed statistics JSON endpoints
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

The XMLTV file will be available at `http://localhost:8080/xmltv.xml` (or `http://localhost:8081/xmltv.xml` if you set `GRACENOTE_PORT=8081` / `TVTV_PORT=8081`)

## Configuration

Configure the application using environment variables (`GRACENOTE_*` is preferred; legacy `TVTV_*` aliases are fully supported):

| Variable (Preferred / Legacy) | Description | Default |
|-------------------------------|-------------|---------|
| `GRACENOTE_TIMEZONE` / `TVTV_TIMEZONE` | Timezone for guide data (see [tz database](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones)) | `America/Phoenix` |
| `GRACENOTE_LINEUPS` / `TVTV_LINEUPS` | Comma-separated list of lineup IDs, each `{zipCode}_{headendId}` (e.g., `85142_OTA,85142_AZ02490`). Each lineup will generate its own XMLTV file. | `85142_OTA` |
| `GRACENOTE_LINEUP_ID` / `TVTV_LINEUP_ID` | (Deprecated when `*_LINEUPS` is set) Single lineup ID, `{zipCode}_{headendId}` | `85142_OTA` |
| `GRACENOTE_DEFAULT_LINEUP` / `TVTV_DEFAULT_LINEUP` | With multiple lineups, which one is served at `/` (must be one of them). If unset, `/` shows a list until one is picked at runtime via `/list`. | `85142_OTA` |
| `GRACENOTE_DAYS` / `TVTV_DAYS` | Number of days to fetch (1-14) | `8` |
| `GRACENOTE_UPDATE_INTERVAL` / `TVTV_UPDATE_INTERVAL` | Update interval in seconds | `3600` |
| `GRACENOTE_PORT` / `TVTV_PORT` | HTTP server port | `8080` |
| `GRACENOTE_HOST` / `TVTV_HOST` | HTTP server host | `0.0.0.0` |
| `GRACENOTE_OUTPUT_FILE` / `TVTV_OUTPUT_FILE` | Output file path (used only for single lineup mode) | `xmltv.xml` |
| `GRACENOTE_MOCK_MODE` / `TVTV_MOCK_MODE` | Use mock data instead of real API (for testing) | `false` |

### Finding Your Lineup ID

Guide data comes from Gracenote's free TV listings API (the same source that powers
[Zap2it](https://tvlistings.zap2it.com/) and [TVGuide.com](https://www.tvguide.com/)).
A lineup ID is `{zipCode}_{headendId}`:

1. For local over-the-air broadcast channels, use the `OTA` sentinel: `85142_OTA`.
2. For a specific cable/satellite provider, look up its headend ID for your zip code:
   ```bash
   curl 'https://tvlistings.gracenote.com/gapzap_webapi/api/Providers/getPostalCodeProviders/USA/85142/gapzap/en'
   ```
   This returns a `Providers` array; each entry's `headendId` combined with your zip
   code is a valid lineup ID, e.g. `headendId: "AZ02490"` → `85142_AZ02490`.

**Multiple Lineups:** You can specify multiple lineup IDs using the `GRACENOTE_LINEUPS` (or `TVTV_LINEUPS`) environment variable with a comma-separated list (e.g., `GRACENOTE_LINEUPS=85142_OTA,85142_AZ02490`). Each lineup will generate its own XMLTV file and be accessible at `/<lineup-id>.xml` (e.g., `/85142_OTA.xml`, `/85142_AZ02490.xml`). The full list of lineups (with links) is always available at `/list`.

**Default Lineup:** With multiple lineups configured, `/` serves the designated default (defaults to `85142_OTA`). You can change this via `GRACENOTE_DEFAULT_LINEUP=85142_OTA` or by clicking "set as default" next to a lineup on the `/list` dashboard page. A runtime pick (via `/list`) is persisted and survives restarts; the env var, if set, always takes precedence.

### Mock Mode for Testing

To test the application without hitting the real API (useful during development):

```bash
export GRACENOTE_MOCK_MODE=true
export GRACENOTE_LINEUPS=85142_OTA,85142_AZ02490
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
docker build -t gracenote2xmltv .

# Run the container
docker run -d \
  -p 8080:8080 \
  -e GRACENOTE_LINEUPS=85142_OTA,85142_AZ02490 \
  -e GRACENOTE_TIMEZONE=America/Phoenix \
  -v xmltv-data:/data \
  gracenote2xmltv
```

**Using Podman:**

```bash
# Build the image
podman build -t gracenote2xmltv .

# Run the container
podman run -d \
  -p 8080:8080 \
  -e GRACENOTE_LINEUPS=85142_OTA,85142_AZ02490 \
  -e GRACENOTE_TIMEZONE=America/Phoenix \
  -v xmltv-data:/data \
  gracenote2xmltv

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
export GRACENOTE_LINEUP_ID=85142_OTA
export GRACENOTE_TIMEZONE=America/Phoenix
python src/main.py --mode serve
```

## Usage

### Server Mode (Default)

Run as an HTTP server that automatically updates the XMLTV file:

```bash
python src/main.py --mode serve
```

Access the XMLTV file at:
- `http://localhost:8080/` or `http://localhost:8080/xmltv.xml` - Download default XMLTV file (`85142_OTA.xml`)
- `http://localhost:8080/85142_OTA.xml` - Download 85142 Over-The-Air guide
- `http://localhost:8080/list` or `http://localhost:8080/dashboard` - Web dashboard
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
   - **Multiple lineups:** `http://your-server:8080/<lineup-id>.xml` (e.g., `http://your-server:8080/85142_OTA.xml`)
3. Set up automatic refresh (recommended: every 12-24 hours)

### Plex

1. Configure Plex DVR settings
2. Add XMLTV source:
   - **Single lineup:** `http://your-server:8080/xmltv.xml`
   - **Multiple lineups:** `http://your-server:8080/<lineup-id>.xml` (e.g., `http://your-server:8080/85142_OTA.xml`)

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
│       ├── gracenote_client.py    # Gracenote grid API client
│       ├── xmltv_generator.py     # XMLTV format generator
│       ├── converter.py           # Main conversion logic
│       └── server.py              # HTTP server
├── tests/
│   ├── test_config.py
│   ├── test_gracenote_client.py
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
- `GET /` - Download XMLTV file (default output)
- `GET /xmltv.xml` - Download XMLTV file (alternative endpoint)
- `GET /list` or `GET /dashboard` - Web dashboard displaying feed statistics (channel count, days, date range, programs count, file size, last refreshed) and on-demand **Reload Feeds** button
- `GET /health` - Health check (returns JSON with status and comprehensive feed statistics)
- `GET /stats` - Feed statistics (returns JSON with channels, days, date range, programs count, and last refreshed)
- `GET|POST /update` - Manually trigger XMLTV feed reload (returns JSON or redirects to `/list?refreshed=1` for browser form submissions)

### Multiple Lineup Mode
- `GET /` - Download the default lineup's XMLTV file (if `TVTV_DEFAULT_LINEUP` is set or one was picked via `/list`); otherwise, show web dashboard (same as `/list`)
- `GET /list` or `GET /dashboard` - Web dashboard with interactive **Reload Feeds** button, cards with full statistics for each lineup, download links, and a "Set as default" action per lineup
- `GET /set-default/<lineup-id>` - Pick which lineup is served at `/` (persisted across restarts)
- `GET /<lineup-id>.xml` - Download XMLTV file for specific lineup (e.g., `/85142_OTA.xml`)
- `GET /health` - Health check (returns JSON with status, lineup list, current default lineup, and feed statistics)
- `GET /stats` - Feed statistics (returns JSON with channels, days, date ranges, programs count, and file sizes for all feeds)
- `GET|POST /update` - Manually trigger XMLTV update for all lineups (returns JSON or redirects to `/list?refreshed=1`)

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
1. Verify your lineup ID's headend exists for your zip code (see "Finding Your Lineup ID" above)
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

## Releasing

Releases and container image builds are automated via **GitHub Actions** (`.github/workflows/docker.yml`).

To initiate a release, use the included [`release.sh`](release.sh) script, which runs local quality checks, synchronizes versions across project files, creates an annotated Git tag (`vX.Y.Z`), and pushes to GitHub. Pushing the tag triggers GitHub Actions to build multi-arch container images (`linux/amd64`, `linux/arm64`) and publish them to GitHub Container Registry (GHCR):

```bash
# Preview release actions without making changes
./release.sh --dry-run

# Release with a patch version bump (e.g. 2.0.0 -> 2.0.1)
./release.sh --patch

# Release with a minor version bump (e.g. 2.0.0 -> 2.1.0)
./release.sh --minor

# Release a specific version
./release.sh 2.1.0

# Release and watch the triggered GitHub Actions workflow live
./release.sh 2.1.0 --watch
```

See `./release.sh --help` for all available options.

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
- [Zap2it](https://tvlistings.zap2it.com/) - Guide data source (Gracenote grid API)

## Support

For issues and questions:
- Open an issue on GitHub
- Check existing issues for solutions
- Review the troubleshooting section
