"""
Integration tests for the converter
"""

import re

import pytest
import responses
from tvtv2xmltv.config import Config
from tvtv2xmltv.converter import TVTVConverter


@pytest.fixture
def test_config():
    """Create a test configuration"""
    config = Config()
    config.lineup_id = "USA-TEST12345"
    config.lineups = ["USA-TEST12345"]
    config.days = 1
    config.output_file = "/tmp/test_xmltv.xml"
    return config


@responses.activate
def test_converter_full_flow(test_config):
    """Test full conversion flow"""
    # Mock lineup data
    lineup_data = [
        {
            "channelNumber": "2.1",
            "stationId": 12345,
            "stationCallSign": "WABC",
            "logo": "/path/to/logo.png",
        }
    ]

    responses.add(
        responses.GET,
        "https://www.tvtv.us/api/v1/lineup/USA-TEST12345/channels",
        json=lineup_data,
        status=200,
    )

    # Mock grid data - need to match the actual API call pattern
    grid_data = [
        [
            {
                "programId": "PR123",
                "title": "Test Show",
                "subtitle": "Test Episode",
                "startTime": "2023-05-23T20:00:00.000Z",
                "duration": 1800,
                "runTime": 30,
                "type": "S",
                "flags": ["HD", "New"],
            }
        ]
    ]

    responses.add(
        responses.GET,
        re.compile(r"https://www.tvtv.us/api/v1/lineup/USA-TEST12345/grid/.*"),
        json=grid_data,
        status=200,
    )

    converter = TVTVConverter(test_config)
    result_dict = converter.convert()

    # Result should be a dict with lineup_id as key
    assert isinstance(result_dict, dict)
    assert "USA-TEST12345" in result_dict

    result = result_dict["USA-TEST12345"]
    assert '<?xml version="1.0" encoding="UTF-8"?>' in result
    assert '<channel id="2.1">' in result
    assert "WABC" in result
    assert "</tv>" in result
