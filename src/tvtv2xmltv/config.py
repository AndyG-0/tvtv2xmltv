"""
Configuration module for tvtv2xmltv
"""

import os


class Config:
    """Configuration class that loads settings from environment variables

    Supports multiple lineups via the `TVTV_LINEUPS` env var (comma-separated).
    Backwards-compatible with the single `TVTV_LINEUP_ID` env var.
    """

    # pylint: disable=too-many-instance-attributes

    def __init__(self):
        self.timezone = os.getenv("TVTV_TIMEZONE", "America/New_York")

        # Support multiple lineups via TVTV_LINEUPS (comma-separated). Fall back
        # to TVTV_LINEUP_ID for backwards compatibility.
        lineup_env = os.getenv("TVTV_LINEUPS")
        if lineup_env:
            # Split by comma and strip whitespace, ignore empty entries
            self.lineups = [lineup.strip() for lineup in lineup_env.split(",") if lineup.strip()]
        else:
            single = os.getenv("TVTV_LINEUP_ID", "30236_OTA")
            self.lineups = [single]

        # Keep `lineup_id` attribute for compatibility with existing code/tests
        self.lineup_id = self.lineups[0]

        # Optional explicit default lineup to serve at "/" in multi-lineup mode.
        # Must match one of the configured lineups; otherwise it's ignored (falling
        # back to a runtime-selected default, handled by the server).
        default_lineup_env = os.getenv("TVTV_DEFAULT_LINEUP")
        if default_lineup_env and default_lineup_env in self.lineups:
            self.default_lineup = default_lineup_env
        else:
            if default_lineup_env:
                print(
                    f"Warning: TVTV_DEFAULT_LINEUP='{default_lineup_env}' is not in "
                    f"TVTV_LINEUPS; ignoring"
                )
            self.default_lineup = None

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

        # Base URL for stream URLs in XMLTV channels (optional)
        self.stream_base_url = os.getenv("TVTV_STREAM_BASE_URL")

        # External URL for source-info-url in XMLTV (optional, defaults to localhost)
        self.external_url = os.getenv("TVTV_EXTERNAL_URL", f"http://localhost:{self.port}")

        # Validate days (max 14, matching the Gracenote grid API's practical range)
        self.days = max(1, min(self.days, 14))
