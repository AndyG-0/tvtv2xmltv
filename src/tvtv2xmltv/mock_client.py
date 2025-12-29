"""
Mock TVTV.us API client for local testing without hitting the real API
"""

import json
import time
from pathlib import Path


class MockTVTVClient:
    """Mock client that returns fixture data instead of making real API calls"""

    def __init__(self, lineup_id, max_retries=3, retry_delay=2):
        self.lineup_id = lineup_id
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.fixtures_dir = Path(__file__).parent.parent.parent / "tests" / "fixtures"

    def _load_fixture(self, filename):
        """Load fixture data from JSON file"""
        filepath = self.fixtures_dir / filename
        if not filepath.exists():
            print(f"Warning: Fixture {filename} not found, returning empty data")
            return []

        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)

    def get_lineup_channels(self):
        """Return mock channel lineup data"""
        print(f"[MOCK] Fetching lineup channels for {self.lineup_id}")
        time.sleep(0.1)  # Simulate network delay

        filename = f"{self.lineup_id}_channels.json"
        return self._load_fixture(filename)

    def get_grid_data(self, start_time, end_time, channels):  # pylint: disable=unused-argument
        """Return mock grid data"""
        print(f"[MOCK] Fetching grid data for {self.lineup_id} ({len(channels)} channels)")
        time.sleep(0.1)  # Simulate network delay

        filename = f"{self.lineup_id}_grid.json"
        return self._load_fixture(filename)
