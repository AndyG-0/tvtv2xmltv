"""
XMLTV format generator module
"""

from datetime import datetime, timedelta
from xml.sax.saxutils import escape  # nosec B406 - We're generating XML, not parsing it
import pytz


class XMLTVGenerator:
    """Generate XMLTV format from TVTV data"""

    def __init__(self, timezone="America/New_York"):
        self.timezone = timezone
        self.tz = pytz.timezone(timezone)

    def generate(self, lineup_data, listings_by_day, source_url="http://localhost:8080"):
        """
        Generate complete XMLTV document.

        Args:
            lineup_data: List of channel dictionaries
            listings_by_day: List of daily listings (each day is a list of channel listings)
            source_url: URL of the data source

        Returns:
            String containing complete XMLTV document
        """
        lines = []
        now = datetime.now(self.tz)
        start_time = now.strftime("%Y-%m-%dT00:00:00.000Z")

        # XML header
        lines.append('<?xml version="1.0" encoding="UTF-8"?>')
        lines.append(
            f'<tv date="{start_time}" source-info-url="{escape(source_url)}" '
            f'source-info-name="tvtv2xmltv">'
        )

        # Add channels
        for channel in lineup_data:
            lines.append(self._generate_channel(channel))

        # Add programs
        for day_listings in listings_by_day:
            for channel_idx, channel in enumerate(lineup_data):
                if channel_idx < len(day_listings):
                    for program in day_listings[channel_idx]:
                        lines.append(self._generate_programme(program, channel))

        lines.append("</tv>")
        return "\r\n".join(lines)

    def _generate_channel(self, channel):
        """Generate channel element"""
        channel_num = escape(str(channel["channelNumber"]))
        call_sign = escape(channel["stationCallSign"])
        logo = escape(f"https://www.tvtv.us{channel['logo']}")

        return (
            f'<channel id="{channel_num}">'
            f"<display-name>{channel_num}</display-name>"
            f"<display-name>{call_sign}</display-name>"
            f'<icon src="{logo}" />'
            f"</channel>"
        )

    def _generate_programme(self, program, channel):
        """Generate programme element"""
        # Parse start time and convert to local timezone
        start_dt = datetime.fromisoformat(program["startTime"].replace("Z", "+00:00"))
        start_dt_local = start_dt.astimezone(self.tz)

        # Calculate end time
        runtime_minutes = program["runTime"]
        end_dt_local = start_dt_local + timedelta(minutes=runtime_minutes)

        # Format times for XMLTV
        start_str = start_dt_local.strftime("%Y%m%d%H%M%S %z")
        end_str = end_dt_local.strftime("%Y%m%d%H%M%S %z")

        channel_num = escape(str(channel["channelNumber"]))
        duration = escape(str(program["duration"]))
        title = escape(program["title"])
        subtitle = escape(program.get("subtitle", ""))

        lines = []
        lines.append(
            f'<programme start="{start_str}" stop="{end_str}" '
            f'duration="{duration}" channel="{channel_num}">'
        )
        lines.append(f'<title lang="en">{title}</title>')

        if subtitle:
            lines.append(f'<sub-title lang="en">{subtitle}</sub-title>')

        # Add categories based on type
        program_type = program.get("type", "")
        if program_type == "M":
            lines.append('<category lang="en">movie</category>')
        elif program_type == "N":
            lines.append('<category lang="en">news</category>')
        elif program_type == "S":
            lines.append('<category lang="en">sports</category>')

        # Add categories and tags based on flags
        flags = program.get("flags", [])
        flags_str = ",".join(flags)

        if "EI" in flags_str:
            lines.append('<category lang="en">kids</category>')

        if "HD" in flags_str:
            lines.append("<video><quality>HDTV</quality></video>")

        if "Stereo" in flags_str:
            lines.append("<audio><stereo>stereo</stereo></audio>")

        if "New" in flags_str:
            lines.append("<new />")

        lines.append("</programme>")
        return "".join(lines)
