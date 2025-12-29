"""
TVTV.us API client module
"""

import time

import requests


class TVTVClient:
    """Client for interacting with the TVTV.us API"""

    BASE_URL = "https://www.tvtv.us/api/v1"

    def __init__(self, lineup_id, max_retries=3, retry_delay=2):
        self.lineup_id = lineup_id
        self.max_retries = max_retries
        self.retry_delay = retry_delay

    def _make_request(self, url):
        """Make HTTP request with retry logic and rate limit handling"""
        for attempt in range(self.max_retries):
            try:
                response = requests.get(url, timeout=30)

                # Handle rate limiting with exponential backoff
                if response.status_code == 429:
                    if attempt < self.max_retries - 1:
                        # Exponential backoff: 5, 10, 20 seconds
                        wait_time = 5 * (2**attempt)
                        print(f"Rate limited (429). Waiting {wait_time}s before retry...")
                        time.sleep(wait_time)
                        continue

                response.raise_for_status()

                # Delay after successful request to avoid rate limiting
                # iptv-org uses 500ms and it works; we use 750ms to be extra safe
                time.sleep(0.75)
                return response.json()
            except requests.RequestException:
                if attempt == self.max_retries - 1:
                    raise
                time.sleep(self.retry_delay * (attempt + 1))

    def get_lineup_channels(self):
        """Fetch channel lineup data"""
        url = f"{self.BASE_URL}/lineup/{self.lineup_id}/channels"
        return self._make_request(url)

    def get_grid_data(self, start_time, end_time, channels):
        """
        Fetch grid data for specified channels and time range.
        Channels should be a list of station IDs.
        Returns listing data.
        """
        # Split channels into batches of 20 to avoid Cloudflare blocks
        all_listings = []
        for i in range(0, len(channels), 20):
            batch = channels[i : i + 20]
            channel_str = ",".join(str(ch) for ch in batch)
            url = (
                f"{self.BASE_URL}/lineup/{self.lineup_id}/grid/"
                f"{start_time}/{end_time}/{channel_str}"
            )

            batch_data = self._make_request(url)
            if batch_data:
                all_listings.extend(batch_data)

            # Delay between batches to avoid rate limiting
            # We already have 750ms delay per request in _make_request
            if i + 20 < len(channels):
                time.sleep(1.5)

        return all_listings
