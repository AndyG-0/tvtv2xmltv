# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
- 78% code coverage
- Continuous integration with GitHub Actions

[1.0.0]: https://github.com/AndyG-0/tvtv2xmltv/releases/tag/v1.0.0
