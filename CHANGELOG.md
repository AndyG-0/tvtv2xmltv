# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased] - 2026-08-20

### Changed
- **Replaced the tvtv.us backend with Gracenote's free consumer grid API**
  (`tvlistings.gracenote.com`, the same backend behind Zap2it.com/TVGuide.com),
  since tvtv.us discontinued its public API (`/api/v1/...` routes now 404;
  the site's current guide is served through a session-bound internal API that
  isn't practical to replicate).
- Lineup IDs now use the format `{zipCode}_{headendId}` (e.g. `85142_OTA` for
  local broadcast, `85142_AZ02490` for a specific cable/satellite provider)
  instead of tvtv.us's opaque lineup IDs.
- Raised `TVTV_DAYS` max from 8 to 14, matching Gracenote's available guide
  window (previously capped by tvtv.us).

### Added
- Support for multiple lineup configurations via `TVTV_LINEUPS` (comma-separated list)
- Each lineup now generates its own separate XMLTV file
- Lineup-specific endpoints: `/<lineup-id>.xml` for accessing individual lineup files
- HTML index page listing all available lineups when multiple lineups are configured
- Mock mode (`TVTV_MOCK_MODE=true`) for testing without hitting the real API
- Mock fixture data for `luUSA-OTA85142` and `luUSA-AZ02490-X` lineups
- `run_server_mock.sh` script for easy mock mode testing

### Changed
- `convert()` method now returns a dictionary mapping lineup IDs to XMLTV data
- `save_to_file()` method now returns a list of saved file paths
- Server mode automatically creates and serves separate files for each lineup
- Health endpoint now includes `lineups` array and `files_exist` boolean
- **Implemented conservative rate limiting to prevent 429 errors:**
  - Delay after each request: **750ms** (1.5x the proven iptv-org value of 500ms)
  - Delay between grid batches: **1.5 seconds**
  - Delay between lineups: **3 seconds**
  - 429 error exponential backoff: **5s → 10s → 20s**
  - See [RATE_LIMITING.md](RATE_LIMITING.md) for detailed strategy

### Deprecated
- `TVTV_LINEUP_ID` is now deprecated in favor of `TVTV_LINEUPS` (still supported for backward compatibility)

## [1.0.0] - 2024-12-28

### Added
- Initial release of tvtv2xmltv
- Python-based converter from tvtv.us to XMLTV format
- HTTP server to serve XMLTV files
- Automatic periodic updates of guide data
- Docker support with Dockerfile and docker-compose.yml
- Comprehensive test suite with pytest
- Configuration via environment variables
- Health check endpoints
- GitHub Actions CI/CD workflows
- Support for multiple timezones
- Batch processing to avoid API rate limits
- Retry logic for failed requests
- Full XMLTV format support including:
  - Channel information (number, call sign, logo)
  - Program details (title, subtitle)
  - Program metadata (categories, HD/stereo flags, new episodes)
  - Accurate start/stop times

### Documentation
- Comprehensive README with usage instructions
- Docker deployment guide
- Integration guides for Jellyfin, Plex, and Emby
- Contributing guidelines
- Example environment configuration

### Testing
- Unit tests for all major components
- Integration tests
- Comprehensive code coverage
- Continuous integration with GitHub Actions

[1.0.0]: https://github.com/AndyG-0/tvtv2xmltv/releases/tag/v1.0.0
