"""
Tests for the Gracenote grid API client
"""

import pytest
import responses
from tvtv2xmltv.gracenote_client import GracenoteClient

PROVIDERS_URL = (
    "https://tvlistings.gracenote.com/gapzap_webapi/api/Providers/"
    "getPostalCodeProviders/USA/85142/gapzap/en"
)
GRID_URL = "https://tvlistings.gracenote.com/api/grid"

PROVIDERS_RESPONSE = {
    "Providers": [
        {
            "type": "OTA",
            "device": "",
            "lineupId": "USA-lineupId-DEFAULT",
            "headendId": "lineupId",
            "postalCode": "85142",
        },
        {
            "type": "CABLE",
            "device": "X",
            "lineupId": "USA-AZ02490-DEFAULT",
            "headendId": "AZ02490",
            "postalCode": "85142",
        },
    ]
}


def _grid_response(channel_id="30817", start_time="2026-01-01T04:00:00Z"):
    return {
        "channels": [
            {
                "callSign": "KTVKDT",
                "channelId": channel_id,
                "channelNo": "3.1",
                "thumbnail": "//zpmc.tmsimg.com/h3/NowShowing/30817/s30817_ll_h15_ab.png?w=55",
                "events": [
                    {
                        "startTime": start_time,
                        "duration": "30",
                        "filter": ["filter-news"],
                        "flag": ["New"],
                        "tags": ["Stereo", "CC"],
                        "program": {
                            "title": "Test Show",
                            "id": "EP123",
                            "tmsId": "EP123",
                            "episodeTitle": None,
                        },
                    }
                ],
            }
        ]
    }


@pytest.fixture
def client():
    """Create a test client for zip 85142, local broadcast"""
    return GracenoteClient.from_lineup_id("85142_OTA")


def test_from_lineup_id_ota_sentinel():
    """Test that the "OTA" sentinel resolves to Gracenote's local-broadcast headendId"""
    result = GracenoteClient.from_lineup_id("85142_OTA")
    assert result.postal_code == "85142"
    assert result.headend_id == "lineupId"


def test_from_lineup_id_headend():
    """Test parsing a specific provider headend id"""
    result = GracenoteClient.from_lineup_id("85142_AZ02490")
    assert result.postal_code == "85142"
    assert result.headend_id == "AZ02490"


def test_from_lineup_id_invalid():
    """Test that a malformed lineup id raises"""
    with pytest.raises(ValueError):
        GracenoteClient.from_lineup_id("no-underscore")


@responses.activate
def test_get_lineup_channels(client):
    """Test fetching and normalizing channel lineup data"""
    responses.add(responses.GET, PROVIDERS_URL, json=PROVIDERS_RESPONSE, status=200)
    responses.add(responses.GET, GRID_URL, json=_grid_response(), status=200)

    result = client.get_lineup_channels()

    assert result == [
        {
            "channelNumber": "3.1",
            "stationId": "30817",
            "stationCallSign": "KTVKDT",
            "logo": "https://zpmc.tmsimg.com/h3/NowShowing/30817/s30817_ll_h15_ab.png?w=55",
        }
    ]


@responses.activate
def test_get_grid_data_maps_event_fields(client):
    """Test that grid events are mapped to the internal programme dict shape"""
    responses.add(responses.GET, PROVIDERS_URL, json=PROVIDERS_RESPONSE, status=200)
    for start_time in (
        "2026-01-01T04:00:00Z",
        "2026-01-01T10:00:00Z",
        "2026-01-01T16:00:00Z",
        "2026-01-01T22:00:00Z",
    ):
        responses.add(
            responses.GET, GRID_URL, json=_grid_response(start_time=start_time), status=200
        )

    result = client.get_grid_data("2026-01-01T04:00:00.000Z", "2026-01-02T03:59:00.000Z", ["30817"])

    assert len(result) == 1
    assert len(result[0]) == 4  # one event per 6h window, 4 windows in a day

    event = result[0][0]
    assert event["title"] == "Test Show"
    assert event["programId"] == "EP123"
    assert event["subtitle"] == ""
    assert event["runTime"] == 30
    assert event["duration"] == 1800
    assert event["type"] == "N"
    assert set(event["flags"]) == {"New", "Stereo", "CC"}


@responses.activate
def test_get_grid_data_orders_by_requested_channels(client):
    """Test that output ordering matches the requested channel list, not response order"""
    responses.add(responses.GET, PROVIDERS_URL, json=PROVIDERS_RESPONSE, status=200)
    grid = {
        "channels": [
            {
                "callSign": "A",
                "channelId": "111",
                "channelNo": "1.1",
                "thumbnail": "//example.com/a.png",
                "events": [],
            },
            {
                "callSign": "B",
                "channelId": "222",
                "channelNo": "2.1",
                "thumbnail": "//example.com/b.png",
                "events": [],
            },
        ]
    }
    responses.add(responses.GET, GRID_URL, json=grid, status=200)

    result = client.get_grid_data(
        "2026-01-01T04:00:00.000Z", "2026-01-01T10:00:00.000Z", ["222", "111"]
    )

    assert result == [[], []]


@responses.activate
def test_request_retry_on_rate_limit(client, monkeypatch):
    """Test that 403 (Gracenote's rate-limit response) triggers a retry"""
    monkeypatch.setattr("tvtv2xmltv.gracenote_client.time.sleep", lambda seconds: None)
    responses.add(responses.GET, PROVIDERS_URL, json=PROVIDERS_RESPONSE, status=200)
    responses.add(responses.GET, GRID_URL, status=403)
    responses.add(responses.GET, GRID_URL, json=_grid_response(), status=200)

    result = client.get_lineup_channels()
    assert len(result) == 1


def test_resolve_lineup_unknown_headend():
    """Test that an unrecognized headendId raises a clear error"""
    client_ = GracenoteClient("85142", "NOT-A-REAL-HEADEND")
    with responses.RequestsMock() as rsps:
        rsps.add(responses.GET, PROVIDERS_URL, json=PROVIDERS_RESPONSE, status=200)
        with pytest.raises(ValueError):
            client_._resolve_lineup()  # pylint: disable=protected-access
