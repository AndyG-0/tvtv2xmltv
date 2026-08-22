# Test Fixtures

This directory contains mock data for testing the application without hitting the real Gracenote API.

## Available Fixtures

### 85142_OTA (Phoenix local broadcast)
- `85142_OTA_channels.json` - Channel lineup (6 channels)
- `85142_OTA_grid.json` - Sample program grid data

### 85142_AZ02490 (Cox Communications, Phoenix)
- `85142_AZ02490_channels.json` - Channel lineup (4 channels)
- `85142_AZ02490_grid.json` - Sample program grid data

## Usage

Set `TVTV_MOCK_MODE=true` to use these fixtures instead of making real API calls:

```bash
export TVTV_MOCK_MODE=true
export TVTV_LINEUPS=85142_OTA,85142_AZ02490
python src/main.py --mode serve
```

Or use the convenience script:

```bash
./run_server_mock.sh
```

## Adding New Fixtures

To add fixtures for a new lineup:

1. Create `{lineup-id}_channels.json` with channel data
2. Create `{lineup-id}_grid.json` with program grid data
3. Add the lineup ID to your `TVTV_LINEUPS` environment variable

The mock client will automatically load these fixtures when in mock mode.
