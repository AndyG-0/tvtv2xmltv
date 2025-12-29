"""
Main converter module that orchestrates the conversion process
"""

import os
from datetime import datetime, timedelta, timezone
from .tvtv_client import TVTVClient
from .mock_client import MockTVTVClient
from .xmltv_generator import XMLTVGenerator


class TVTVConverter:
    """Main converter class that coordinates fetching and conversion"""

    def __init__(self, config):
        self.config = config
        # Don't create a single client here: each lineup has its own client
        self.generator = XMLTVGenerator(config.timezone)

    def convert_lineup(self, lineup_id):
        """
        Fetch data from TVTV for a single lineup and convert to XMLTV format.

        Args:
            lineup_id: The lineup ID to fetch and convert

        Returns:
            String containing XMLTV formatted data for this lineup
        """
        # Use mock client if mock mode is enabled
        if self.config.mock_mode:
            print(f"[MOCK MODE] Using mock data for {lineup_id}")
            client = MockTVTVClient(lineup_id)
        else:
            client = TVTVClient(lineup_id)

        # Get channel lineup
        lineup_data = client.get_lineup_channels()
        if not lineup_data:
            raise ValueError(f"Failed to fetch lineup data for {lineup_id}")

        # Extract station IDs for grid queries with validation
        all_channels = []
        for channel in lineup_data:
            if isinstance(channel, dict) and "stationId" in channel:
                all_channels.append(channel["stationId"])
        
        if not all_channels:
            raise ValueError("No valid stationId values found in lineup data")

        # Fetch grid data for each day
        listings_by_day = []
        for day in range(self.config.days):
            now = datetime.now(timezone.utc)
            start = now + timedelta(days=day)
            end = now + timedelta(days=day + 1)

            # Format times for API
            start_time = start.strftime("%Y-%m-%dT04:00:00.000Z")
            end_time = end.strftime("%Y-%m-%dT03:59:00.000Z")

            # Fetch grid data
            day_listings = client.get_grid_data(start_time, end_time, all_channels)
            if day_listings:
                listings_by_day.append(day_listings)

        # Generate XMLTV
        source_url = f"http://localhost:{self.config.port}/{lineup_id}.xml"
        xmltv_data = self.generator.generate(lineup_data, listings_by_day, source_url)

        return xmltv_data

    def convert(self):
        """
        Fetch data from TVTV for all configured lineups and convert to XMLTV format.

        Returns:
            Dictionary mapping lineup_id to XMLTV formatted data string
        """
        import time

        results = {}
        for i, lineup_id in enumerate(self.config.lineups):
            # Add delay between lineups to avoid rate limiting (except for first)
            if i > 0:
                delay = 3  # 3 seconds between lineups
                print(f"Waiting {delay}s before fetching next lineup...")
                time.sleep(delay)

            results[lineup_id] = self.convert_lineup(lineup_id)
        return results

    def save_to_file(self, filename=None):
        """
        Convert and save XMLTV data to file(s).

        For single lineup: saves to filename or config.output_file
        For multiple lineups: saves to {lineup_id}.xml for each lineup in current directory

        Args:
            filename: Output filename (only used for single lineup mode)

        Returns:
            List of absolute paths to saved files
        """
        xmltv_data_dict = self.convert()

        saved_files = []

        if len(self.config.lineups) == 1:
            # Single lineup: save to specified filename or default
            if filename is None:
                filename = self.config.output_file

            lineup_id = self.config.lineups[0]
            xmltv_data = xmltv_data_dict[lineup_id]

            # Use absolute path
            abs_filename = os.path.abspath(filename)

            with open(abs_filename, "w", encoding="utf-8") as f:
                f.write(xmltv_data)

            saved_files.append(abs_filename)
        else:
            # Multiple lineups: save each to {lineup_id}.xml in current directory
            for lineup_id, xmltv_data in xmltv_data_dict.items():
                output_filename = f"{lineup_id}.xml"

                # Use absolute path
                abs_filename = os.path.abspath(output_filename)

                with open(abs_filename, "w", encoding="utf-8") as f:
                    f.write(xmltv_data)

                saved_files.append(abs_filename)

        return saved_files
