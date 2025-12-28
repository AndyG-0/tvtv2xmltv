"""
Configuration module for tvtv2xmltv
"""

import os


class Config:
    """Configuration class that loads settings from environment variables"""

    def __init__(self):
        self.timezone = os.getenv("TVTV_TIMEZONE", "America/New_York")
        self.lineup_id = os.getenv("TVTV_LINEUP_ID", "USA-OTA30236")
        self.days = int(os.getenv("TVTV_DAYS", "8"))
        self.output_file = os.getenv("TVTV_OUTPUT_FILE", "xmltv.xml")
        self.update_interval = int(os.getenv("TVTV_UPDATE_INTERVAL", "3600"))
        self.port = int(os.getenv("TVTV_PORT", "8080"))
        # Binding to 0.0.0.0 is intentional for Docker/server deployment
        self.host = os.getenv("TVTV_HOST", "0.0.0.0")  # nosec B104

        # Validate days (max 8)
        if self.days > 8:
            self.days = 8
        if self.days < 1:
            self.days = 1
