"""
TVTV.us API client module
"""
import requests
import time


class TVTVClient:
    """Client for interacting with the TVTV.us API"""
    
    BASE_URL = "https://www.tvtv.us/api/v1"
    
    def __init__(self, lineup_id, max_retries=3, retry_delay=1):
        self.lineup_id = lineup_id
        self.max_retries = max_retries
        self.retry_delay = retry_delay
    
    def _make_request(self, url):
        """Make HTTP request with retry logic"""
        for attempt in range(self.max_retries):
            try:
                response = requests.get(url, timeout=30)
                response.raise_for_status()
                return response.json()
            except requests.RequestException as e:
                if attempt == self.max_retries - 1:
                    raise
                time.sleep(self.retry_delay * (attempt + 1))
        return None
    
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
            batch = channels[i:i+20]
            channel_str = ','.join(str(ch) for ch in batch)
            url = f"{self.BASE_URL}/lineup/{self.lineup_id}/grid/{start_time}/{end_time}/{channel_str}"
            
            batch_data = self._make_request(url)
            if batch_data:
                all_listings.extend(batch_data)
            
            # Small delay between batches to be nice to the API
            if i + 20 < len(channels):
                time.sleep(0.5)
        
        return all_listings
