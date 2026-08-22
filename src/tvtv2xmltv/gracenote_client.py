"""
Gracenote TV listings grid API client module

Uses the free, unauthenticated consumer grid API that backs
tvlistings.gracenote.com (the same backend behind Zap2it.com and TVGuide.com),
as a replacement for tvtv.us's now-defunct public API.
"""

import time
from datetime import datetime, timedelta, timezone

import requests


class GracenoteClient:
    """Client for fetching TV listings from Gracenote's free consumer grid API"""

    BASE_URL = "https://tvlistings.gracenote.com"
    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "application/json, text/plain, */*",
        "Referer": "https://tvlistings.gracenote.com/",
    }
    # Gracenote's /api/grid endpoint rejects any timespan over 6 hours (400 Bad request)
    TIMESPAN_HOURS = 6

    # pylint: disable-next=too-many-arguments,too-many-positional-arguments
    def __init__(self, postal_code, headend_id, country="USA", max_retries=3, retry_delay=2):
        self.postal_code = postal_code
        self.headend_id = headend_id
        self.country = country
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self._lineup_id = None
        self._device = None

    @classmethod
    def from_lineup_id(cls, lineup_id, max_retries=3, retry_delay=2):
        """
        Build a client from a "{postalCode}_{headendId}" lineup id
        (e.g. "85142_OTA" for local broadcast, "85142_AZ02490" for a specific
        cable/satellite provider's headend).
        """
        postal_code, sep, headend_id = lineup_id.partition("_")
        if not sep or not postal_code or not headend_id:
            raise ValueError(
                f"Invalid lineup id {lineup_id!r}; expected '{{postalCode}}_{{headendId}}'"
            )
        # Gracenote's own headendId for local broadcast is the literal string "lineupId"
        if headend_id == "OTA":
            headend_id = "lineupId"
        return cls(postal_code, headend_id, max_retries=max_retries, retry_delay=retry_delay)

    # pylint: disable=inconsistent-return-statements
    def _make_request(self, url, params=None):
        """Make HTTP request with retry logic and rate limit handling"""
        for attempt in range(self.max_retries):
            try:
                response = requests.get(url, params=params, headers=self.HEADERS, timeout=30)

                # Gracenote rate limits by returning 403 (not 429) when hit too fast
                if response.status_code in (403, 429):
                    if attempt < self.max_retries - 1:
                        wait_time = 5 * (2**attempt)
                        print(
                            f"Rate limited ({response.status_code}). "
                            f"Waiting {wait_time}s before retry..."
                        )
                        time.sleep(wait_time)
                        continue

                response.raise_for_status()

                # Delay after successful request to avoid rate limiting
                time.sleep(0.75)
                return response.json()
            except requests.RequestException:
                if attempt == self.max_retries - 1:
                    raise
                time.sleep(self.retry_delay * (attempt + 1))

    def _resolve_lineup(self):
        """Look up the exact lineupId/device for our headend, once per client"""
        if self._lineup_id is not None:
            return

        url = (
            f"{self.BASE_URL}/gapzap_webapi/api/Providers/getPostalCodeProviders/"
            f"{self.country}/{self.postal_code}/gapzap/en"
        )
        data = self._make_request(url)
        providers = (data or {}).get("Providers", [])

        for provider in providers:
            if provider.get("headendId") == self.headend_id:
                self._lineup_id = provider["lineupId"]
                self._device = provider.get("device", "")
                return

        raise ValueError(
            f"No provider with headendId={self.headend_id!r} found for postal code "
            f"{self.postal_code!r}"
        )

    def _fetch_grid_window(self, start_time):
        """Fetch one grid window (up to TIMESPAN_HOURS long) starting at `start_time`"""
        self._resolve_lineup()
        params = {
            "lineupId": self._lineup_id,
            "headendId": self.headend_id,
            "device": self._device,
            "country": self.country,
            "postalCode": self.postal_code,
            "time": int(start_time.timestamp()),
            "timespan": self.TIMESPAN_HOURS,
            "isOverride": "true",
            "pref": "m,p",
            "userId": "-",
            "aid": "orbebb",
        }
        data = self._make_request(f"{self.BASE_URL}/api/grid", params=params)
        return (data or {}).get("channels", [])

    def get_lineup_channels(self):
        """Fetch channel lineup data"""
        channels = self._fetch_grid_window(datetime.now(timezone.utc))
        return [
            {
                "channelNumber": channel["channelNo"],
                "stationId": channel["channelId"],
                "stationCallSign": channel["callSign"],
                "logo": f"https:{channel['thumbnail']}",
            }
            for channel in channels
        ]

    def get_grid_data(self, start_time, end_time, channels):
        """
        Fetch grid data for the given window, paged in TIMESPAN_HOURS-sized steps.

        start_time/end_time are ISO strings like "%Y-%m-%dT04:00:00.000Z".
        channels is a list of stationIds; the returned list-of-lists is ordered
        to match it.
        """
        start_dt = datetime.strptime(start_time, "%Y-%m-%dT%H:%M:%S.%fZ").replace(
            tzinfo=timezone.utc
        )
        end_dt = datetime.strptime(end_time, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=timezone.utc)

        events_by_channel = {str(channel_id): [] for channel_id in channels}

        window_start = start_dt
        first_window = True
        while window_start < end_dt:
            if not first_window:
                time.sleep(1.5)
            first_window = False

            for channel in self._fetch_grid_window(window_start):
                channel_id = str(channel["channelId"])
                if channel_id not in events_by_channel:
                    continue
                for event in channel["events"]:
                    events_by_channel[channel_id].append(self._map_event(event))

            window_start += timedelta(hours=self.TIMESPAN_HOURS)

        return [events_by_channel[str(channel_id)] for channel_id in channels]

    @staticmethod
    def _map_event(event):
        """Map a Gracenote grid event into the internal programme dict shape"""
        program = event.get("program") or {}
        filters = event.get("filter") or []

        if "filter-movie" in filters:
            program_type = "M"
        elif "filter-news" in filters:
            program_type = "N"
        elif "filter-sports" in filters:
            program_type = "S"
        else:
            program_type = ""

        duration_minutes = int(event["duration"])

        return {
            "programId": program.get("tmsId") or program.get("id"),
            "title": program.get("title", ""),
            "subtitle": program.get("episodeTitle") or "",
            "startTime": event["startTime"],
            "duration": duration_minutes * 60,
            "runTime": duration_minutes,
            "type": program_type,
            "flags": list(set((event.get("flag") or []) + (event.get("tags") or []))),
        }
