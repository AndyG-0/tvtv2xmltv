# Test Fixtures

This directory contains mock data for testing the application without hitting the real tvtv.us API.

## Available Fixtures

### luUSA-OTA85142 (Phoenix OTA)
- `luUSA-OTA85142_channels.json` - Channel lineup (6 channels)
- `luUSA-OTA85142_grid.json` - Sample program grid data

### luUSA-AZ02490-X (Alternative Phoenix lineup)
- `luUSA-AZ02490-X_channels.json` - Channel lineup (4 channels)
- `luUSA-AZ02490-X_grid.json` - Sample program grid data

## Usage

Set `TVTV_MOCK_MODE=true` to use these fixtures instead of making real API calls:

```bash
export TVTV_MOCK_MODE=true
export TVTV_LINEUPS=luUSA-OTA85142,luUSA-AZ02490-X
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
