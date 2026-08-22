"""
Configuration module for tvtv2xmltv
"""

import os


def _get_env(gracenote_key, tvtv_key, default=None):
    """Retrieve an environment variable prioritizing GRACENOTE_* over TVTV_*"""
    val = os.getenv(gracenote_key)
    if val is not None:
        return val
    return os.getenv(tvtv_key, default)


class Config:
    """Configuration class that loads settings from environment variables

    Supports GRACENOTE_* environment variables with TVTV_* aliases for backward compatibility.
    Supports multiple lineups via GRACENOTE_LINEUPS / TVTV_LINEUPS (comma-separated).
    """

    # pylint: disable=too-many-instance-attributes

    def __init__(self):
        self.timezone = _get_env("GRACENOTE_TIMEZONE", "TVTV_TIMEZONE", "America/Phoenix")

        # Support multiple lineups via GRACENOTE_LINEUPS / TVTV_LINEUPS (comma-separated).
        # Fall back to GRACENOTE_LINEUP_ID / TVTV_LINEUP_ID for backwards compatibility.
        lineup_env = _get_env("GRACENOTE_LINEUPS", "TVTV_LINEUPS")
        if lineup_env:
            # Split by comma and strip whitespace, ignore empty entries
            self.lineups = [lineup.strip() for lineup in lineup_env.split(",") if lineup.strip()]
        else:
            single = _get_env("GRACENOTE_LINEUP_ID", "TVTV_LINEUP_ID", "85142_OTA")
            self.lineups = [single]

        # Keep `lineup_id` attribute for compatibility with existing code/tests
        self.lineup_id = self.lineups[0]

        # Optional explicit default lineup to serve at "/" in multi-lineup mode.
        # Must match one of the configured lineups; otherwise it's ignored (falling
        # back to a runtime-selected default, handled by the server).
        default_lineup_env = _get_env("GRACENOTE_DEFAULT_LINEUP", "TVTV_DEFAULT_LINEUP")
        if default_lineup_env and default_lineup_env in self.lineups:
            self.default_lineup = default_lineup_env
        else:
            if default_lineup_env:
                print(
                    f"Warning: DEFAULT_LINEUP='{default_lineup_env}' is not in "
                    f"configured lineups; ignoring"
                )
            self.default_lineup = None

        # Parse integer environment variables with validation
        try:
            self.days = int(_get_env("GRACENOTE_DAYS", "TVTV_DAYS", "8"))
        except ValueError:
            self.days = 8

        self.output_file = _get_env("GRACENOTE_OUTPUT_FILE", "TVTV_OUTPUT_FILE", "xmltv.xml")

        try:
            self.update_interval = int(
                _get_env("GRACENOTE_UPDATE_INTERVAL", "TVTV_UPDATE_INTERVAL", "3600")
            )
        except ValueError:
            self.update_interval = 3600

        try:
            self.port = int(_get_env("GRACENOTE_PORT", "TVTV_PORT", "8080"))
        except ValueError:
            self.port = 8080
        # Binding to 0.0.0.0 is intentional for Docker/server deployment
        self.host = _get_env("GRACENOTE_HOST", "TVTV_HOST", "0.0.0.0")  # nosec B104

        # Mock mode for local testing without hitting the real API
        mock_env = _get_env("GRACENOTE_MOCK_MODE", "TVTV_MOCK_MODE", "false")
        self.mock_mode = str(mock_env).lower() in ("true", "1", "yes")

        # Base URL for stream URLs in XMLTV channels (optional)
        self.stream_base_url = _get_env("GRACENOTE_STREAM_BASE_URL", "TVTV_STREAM_BASE_URL")

        # External URL for source-info-url in XMLTV (optional, defaults to localhost)
        self.external_url = _get_env(
            "GRACENOTE_EXTERNAL_URL", "TVTV_EXTERNAL_URL", f"http://localhost:{self.port}"
        )

        # Validate days (max 14, matching the Gracenote grid API's practical range)
        self.days = max(1, min(self.days, 14))
