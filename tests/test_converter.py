"""
Integration tests for the converter
"""

import pytest
import responses
from tvtv2xmltv.config import Config
from tvtv2xmltv.converter import TVTVConverter

PROVIDERS_URL = (
    "https://tvlistings.gracenote.com/gapzap_webapi/api/Providers/"
    "getPostalCodeProviders/USA/12345/gapzap/en"
)
GRID_URL = "https://tvlistings.gracenote.com/api/grid"


@pytest.fixture
def test_config():
    """Create a test configuration"""
    config = Config()
    config.lineup_id = "12345_OTA"
    config.lineups = ["12345_OTA"]
    config.days = 1
    config.output_file = "/tmp/test_xmltv.xml"
    return config


@responses.activate
def test_converter_full_flow(test_config, monkeypatch):
    """Test full conversion flow"""
    monkeypatch.setattr("tvtv2xmltv.gracenote_client.time.sleep", lambda seconds: None)
    responses.add(
        responses.GET,
        PROVIDERS_URL,
        json={
            "Providers": [
                {
                    "type": "OTA",
                    "device": "",
                    "lineupId": "USA-lineupId-DEFAULT",
                    "headendId": "lineupId",
                    "postalCode": "12345",
                }
            ]
        },
        status=200,
    )

    grid_data = {
        "channels": [
            {
                "callSign": "WABC",
                "channelId": "12345",
                "channelNo": "2.1",
                "thumbnail": "//example.com/logo.png",
                "events": [
                    {
                        "startTime": "2023-05-23T20:00:00Z",
                        "duration": "30",
                        "filter": ["filter-news"],
                        "flag": ["New"],
                        "tags": [],
                        "program": {
                            "title": "Test Show",
                            "id": "PR123",
                            "tmsId": "PR123",
                            "episodeTitle": "Test Episode",
                        },
                    }
                ],
            }
        ]
    }

    responses.add(responses.GET, GRID_URL, json=grid_data, status=200)

    converter = TVTVConverter(test_config)
    result_dict = converter.convert()

    # Result should be a dict with lineup_id as key
    assert isinstance(result_dict, dict)
    assert "12345_OTA" in result_dict

    result = result_dict["12345_OTA"]
    assert '<?xml version="1.0" encoding="UTF-8"?>' in result
    assert '<channel id="2.1">' in result
    assert "WABC" in result
    assert "</tv>" in result

    # Check stats
    stats = converter.get_stats("12345_OTA")
    assert stats is not None
    assert stats["channels"] == 1
    assert stats["days"] == 1
    assert stats["programs"] == 4
    assert stats["lineup_id"] == "12345_OTA"
    assert stats["start_date"] == "2023-05-23"
    assert stats["end_date"] == "2023-05-23"
    assert stats["date_range"] == "2023-05-23"
    assert stats["dates"] == ["2023-05-23"]
    assert stats["last_refreshed"] is not None


@responses.activate
def test_converter_save_to_file_populates_stats(test_config, tmp_path, monkeypatch):
    """Test that save_to_file populates file_path, file_size_bytes, and file_size_human in stats"""
    monkeypatch.setattr("tvtv2xmltv.gracenote_client.time.sleep", lambda seconds: None)
    responses.add(
        responses.GET,
        PROVIDERS_URL,
        json={
            "Providers": [
                {
                    "type": "OTA",
                    "device": "",
                    "lineupId": "USA-lineupId-DEFAULT",
                    "headendId": "lineupId",
                    "postalCode": "12345",
                }
            ]
        },
        status=200,
    )
    grid_data = {
        "channels": [
            {
                "callSign": "WABC",
                "channelId": "12345",
                "channelNo": "2.1",
                "thumbnail": "//example.com/logo.png",
                "events": [
                    {
                        "startTime": "2023-05-23T20:00:00Z",
                        "duration": "30",
                        "filter": [],
                        "flag": [],
                        "tags": [],
                        "program": {
                            "title": "Test Show",
                            "id": "PR123",
                        },
                    }
                ],
            }
        ]
    }
    responses.add(responses.GET, GRID_URL, json=grid_data, status=200)

    out_file = str(tmp_path / "saved_guide.xml")
    converter = TVTVConverter(test_config)
    saved_files = converter.save_to_file(out_file)

    assert len(saved_files) == 1
    stats = converter.get_stats("12345_OTA")
    assert stats["file_path"] == out_file
    assert stats["file_size_bytes"] > 0
    assert stats["file_size_human"] != "N/A"
    assert stats["channels"] == 1
    assert stats["days"] == 1
    assert stats["programs"] == 4
    assert converter.get_stats() == converter.stats


def test_format_file_size():
    """Test human-readable file size formatting"""
    from tvtv2xmltv.converter import format_file_size

    assert format_file_size(None) == "N/A"
    assert format_file_size(500) == "500 B"
    assert format_file_size(1024) == "1.0 KB"
    assert format_file_size(1536) == "1.5 KB"
    assert format_file_size(1048576) == "1.0 MB"
    assert format_file_size(1073741824) == "1.0 GB"
