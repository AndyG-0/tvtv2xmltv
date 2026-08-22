"""
Main converter module that orchestrates the conversion process
"""

import os
import time
from datetime import datetime, timedelta, timezone
from .gracenote_client import GracenoteClient
from .mock_client import MockTVTVClient
from .xmltv_generator import XMLTVGenerator


class TVTVConverter:
    """Main converter class that coordinates fetching and conversion"""

    def __init__(self, config):
        self.config = config
        # Don't create a single client here: each lineup has its own client
        self.generator = XMLTVGenerator(config.timezone, config.stream_base_url)
        self.stats = {}

    def _calculate_stats(self, lineup_id, lineup_data, listings_by_day):
        """
        Calculate statistics for a single converted lineup.

        Args:
            lineup_id: The lineup identifier
            lineup_data: List of channel dictionaries
            listings_by_day: List of daily listings (each day is a list of channel events)

        Returns:
            Dictionary containing feed statistics
        """
        channel_count = len(lineup_data) if lineup_data else 0
        dates_covered = set()
        total_programs = 0

        for day_listings in listings_by_day:
            for channel_events in day_listings:
                total_programs += len(channel_events)
                for event in channel_events:
                    start_time = event.get("startTime")
                    if start_time:
                        try:
                            dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
                            dt_local = dt.astimezone(self.generator.tz)
                            dates_covered.add(dt_local.date())
                        except Exception:  # pylint: disable=broad-except
                            dates_covered.add(start_time[:10])

        days_available = len(dates_covered)

        return {
            "lineup_id": lineup_id,
            "channels": channel_count,
            "days": days_available,
            "programs": total_programs,
            "days_requested": self.config.days,
            "file_path": None,
            "file_size_bytes": None,
        }

    def get_stats(self, lineup_id=None):
        """
        Get statistics for a specific lineup or all lineups.

        Args:
            lineup_id: Optional lineup ID to get stats for

        Returns:
            Dictionary of stats for a single lineup, or dictionary of all lineups' stats
        """
        if lineup_id is not None:
            return self.stats.get(lineup_id)
        return self.stats

    def convert_lineup(self, lineup_id):
        """
        Fetch data from TVTV for a single lineup and convert to XMLTV format.

        Args:
            lineup_id: The lineup ID to fetch and convert

        Returns:
            String containing XMLTV formatted data for this lineup
        """
        # pylint: disable=too-many-locals
        # Use mock client if mock mode is enabled
        if self.config.mock_mode:
            print(f"[MOCK MODE] Using mock data for {lineup_id}")
            client = MockTVTVClient(lineup_id)
        else:
            client = GracenoteClient.from_lineup_id(lineup_id)

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
        source_url = f"{self.config.external_url}/{lineup_id}.xml"
        xmltv_data = self.generator.generate(lineup_data, listings_by_day, source_url)

        # Record statistics for this lineup
        self.stats[lineup_id] = self._calculate_stats(lineup_id, lineup_data, listings_by_day)

        return xmltv_data

    def convert(self):
        """
        Fetch data from TVTV for all configured lineups and convert to XMLTV format.

        Returns:
            Dictionary mapping lineup_id to XMLTV formatted data string
        """
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

            if lineup_id in self.stats:
                self.stats[lineup_id]["file_path"] = abs_filename
                self.stats[lineup_id]["file_size_bytes"] = os.path.getsize(abs_filename)

            saved_files.append(abs_filename)
        else:
            # Multiple lineups: save each to {lineup_id}.xml in current directory
            for lineup_id, xmltv_data in xmltv_data_dict.items():
                output_filename = f"{lineup_id}.xml"

                # Use absolute path
                abs_filename = os.path.abspath(output_filename)

                with open(abs_filename, "w", encoding="utf-8") as f:
                    f.write(xmltv_data)

                if lineup_id in self.stats:
                    self.stats[lineup_id]["file_path"] = abs_filename
                    self.stats[lineup_id]["file_size_bytes"] = os.path.getsize(abs_filename)

                saved_files.append(abs_filename)

        return saved_files
