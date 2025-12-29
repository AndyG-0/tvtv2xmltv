"""
Tests for the TVTV API client
"""

import pytest
import responses
from tvtv2xmltv.tvtv_client import TVTVClient


@pytest.fixture
def client():
    """Create a test client"""
    return TVTVClient("USA-TEST12345")


@responses.activate
def test_get_lineup_channels(client):
    """Test fetching lineup channels"""
    mock_data = [
        {
            "channelNumber": "2.1",
            "stationId": 12345,
            "stationCallSign": "WABC",
            "logo": "/path/to/logo.png",
        },
        {
            "channelNumber": "4.1",
            "stationId": 12346,
            "stationCallSign": "WNBC",
            "logo": "/path/to/logo2.png",
        },
    ]

    responses.add(
        responses.GET,
        "https://www.tvtv.us/api/v1/lineup/USA-TEST12345/channels",
        json=mock_data,
        status=200,
    )

    result = client.get_lineup_channels()
    assert result == mock_data
    assert len(result) == 2
    assert result[0]["channelNumber"] == "2.1"


@responses.activate
def test_get_grid_data(client):
    """Test fetching grid data"""
    mock_data = [
        [
            {
                "programId": "PR123",
                "title": "Test Show",
                "subtitle": "Test Episode",
                "startTime": "2023-05-23T04:00:00.000Z",
                "duration": 1800,
                "runTime": 30,
                "type": "S",
                "flags": ["HD", "New"],
            }
        ]
    ]

    responses.add(
        responses.GET,
        "https://www.tvtv.us/api/v1/lineup/USA-TEST12345/grid/"
        "2023-05-23T04:00:00.000Z/2023-05-24T03:59:00.000Z/12345",
        json=mock_data,
        status=200,
    )

    result = client.get_grid_data("2023-05-23T04:00:00.000Z", "2023-05-24T03:59:00.000Z", [12345])

    assert len(result) == 1
    assert result[0][0]["title"] == "Test Show"


@responses.activate
def test_get_grid_data_batching(client):
    """Test that grid data is fetched in batches of 20"""
    # Create 25 channels to trigger batching
    channels = list(range(1000, 1025))

    # Mock first batch (20 channels)
    responses.add(
        responses.GET,
        "https://www.tvtv.us/api/v1/lineup/USA-TEST12345/grid/"
        "2023-05-23T04:00:00.000Z/2023-05-24T03:59:00.000Z/"
        + ",".join(str(c) for c in channels[:20]),
        json=[[] for _ in range(20)],
        status=200,
    )

    # Mock second batch (5 channels)
    responses.add(
        responses.GET,
        "https://www.tvtv.us/api/v1/lineup/USA-TEST12345/grid/"
        "2023-05-23T04:00:00.000Z/2023-05-24T03:59:00.000Z/"
        + ",".join(str(c) for c in channels[20:25]),
        json=[[] for _ in range(5)],
        status=200,
    )

    result = client.get_grid_data("2023-05-23T04:00:00.000Z", "2023-05-24T03:59:00.000Z", channels)

    assert len(result) == 25
    assert len(responses.calls) == 2


@responses.activate
def test_request_retry_on_failure(client):
    """Test that requests are retried on failure"""
    client_with_retry = TVTVClient("USA-TEST12345", max_retries=3, retry_delay=0.1)

    # First two calls fail, third succeeds
    responses.add(
        responses.GET, "https://www.tvtv.us/api/v1/lineup/USA-TEST12345/channels", status=500
    )
    responses.add(
        responses.GET, "https://www.tvtv.us/api/v1/lineup/USA-TEST12345/channels", status=500
    )
    responses.add(
        responses.GET,
        "https://www.tvtv.us/api/v1/lineup/USA-TEST12345/channels",
        json=[],
        status=200,
    )

    result = client_with_retry.get_lineup_channels()
    assert result == []
    assert len(responses.calls) == 3
