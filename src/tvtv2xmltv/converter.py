"""
Main converter module that orchestrates the conversion process
"""
from datetime import datetime, timedelta
from .tvtv_client import TVTVClient
from .xmltv_generator import XMLTVGenerator


class TVTVConverter:
    """Main converter class that coordinates fetching and conversion"""
    
    def __init__(self, config):
        self.config = config
        self.client = TVTVClient(config.lineup_id)
        self.generator = XMLTVGenerator(config.timezone)
    
    def convert(self):
        """
        Fetch data from TVTV and convert to XMLTV format.
        
        Returns:
            String containing XMLTV formatted data
        """
        # Get channel lineup
        lineup_data = self.client.get_lineup_channels()
        if not lineup_data:
            raise ValueError("Failed to fetch lineup data")
        
        # Extract station IDs for grid queries
        all_channels = [channel['stationId'] for channel in lineup_data]
        
        # Fetch grid data for each day
        listings_by_day = []
        for day in range(self.config.days):
            now = datetime.utcnow()
            start = now + timedelta(days=day)
            end = now + timedelta(days=day + 1)
            
            # Format times for API
            start_time = start.strftime('%Y-%m-%dT04:00:00.000Z')
            end_time = end.strftime('%Y-%m-%dT03:59:00.000Z')
            
            # Fetch grid data
            day_listings = self.client.get_grid_data(start_time, end_time, all_channels)
            if day_listings:
                listings_by_day.append(day_listings)
        
        # Generate XMLTV
        source_url = f"http://localhost:{self.config.port}"
        xmltv_data = self.generator.generate(lineup_data, listings_by_day, source_url)
        
        return xmltv_data
    
    def save_to_file(self, filename=None):
        """
        Convert and save XMLTV data to file.
        
        Args:
            filename: Output filename (uses config default if not specified)
        
        Returns:
            Path to saved file
        """
        if filename is None:
            filename = self.config.output_file
        
        xmltv_data = self.convert()
        
        with open(filename, 'w', encoding='iso-8859-1') as f:
            f.write(xmltv_data)
        
        return filename
