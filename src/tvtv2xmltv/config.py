"""
Configuration module for tvtv2xmltv
"""

import os


class Config:
    """Configuration class that loads settings from environment variables

    Supports multiple lineups via the `TVTV_LINEUPS` env var (comma-separated).
    Backwards-compatible with the single `TVTV_LINEUP_ID` env var.
    """

    def __init__(self):
        self.timezone = os.getenv("TVTV_TIMEZONE", "America/New_York")

        # Support multiple lineups via TVTV_LINEUPS (comma-separated). Fall back
        # to TVTV_LINEUP_ID for backwards compatibility.
        lineup_env = os.getenv("TVTV_LINEUPS")
        if lineup_env:
            # Split by comma and strip whitespace, ignore empty entries
            self.lineups = [lineup.strip() for lineup in lineup_env.split(",") if lineup.strip()]
        else:
            single = os.getenv("TVTV_LINEUP_ID", "USA-OTA30236")
            self.lineups = [single]

        # Keep `lineup_id` attribute for compatibility with existing code/tests
        self.lineup_id = self.lineups[0]

        # Parse integer environment variables with validation
        try:
            self.days = int(os.getenv("TVTV_DAYS", "8"))
        except ValueError:
            self.days = 8
        
        self.output_file = os.getenv("TVTV_OUTPUT_FILE", "xmltv.xml")
        
        try:
            self.update_interval = int(os.getenv("TVTV_UPDATE_INTERVAL", "3600"))
        except ValueError:
            self.update_interval = 3600
        
        try:
            self.port = int(os.getenv("TVTV_PORT", "8080"))
        except ValueError:
            self.port = 8080
        # Binding to 0.0.0.0 is intentional for Docker/server deployment
        self.host = os.getenv("TVTV_HOST", "0.0.0.0")  # nosec B104

        # Mock mode for local testing without hitting the real API
        self.mock_mode = os.getenv("TVTV_MOCK_MODE", "false").lower() in ("true", "1", "yes")

        # Validate days (max 8)
        if self.days > 8:
            self.days = 8
        if self.days < 1:
            self.days = 1
