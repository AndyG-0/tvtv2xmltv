"""
Tests for the XMLTV generator
"""

import pytest
from tvtv2xmltv.xmltv_generator import XMLTVGenerator


@pytest.fixture
def generator():
    """Create a test generator"""
    return XMLTVGenerator("America/New_York")


def test_generate_channel():
    """Test channel generation"""
    gen = XMLTVGenerator()
    channel = {"channelNumber": "2.1", "stationCallSign": "WABC", "logo": "/path/to/logo.png"}

    result = gen._generate_channel(channel)
    assert '<channel id="2.1">' in result
    assert "<display-name>2.1</display-name>" in result
    assert "<display-name>WABC</display-name>" in result
    assert "https://www.tvtv.us/path/to/logo.png" in result


def test_generate_programme():
    """Test programme generation"""
    gen = XMLTVGenerator("America/New_York")

    program = {
        "programId": "PR123",
        "title": "Test Show",
        "subtitle": "Test Episode",
        "startTime": "2023-05-23T20:00:00.000Z",
        "duration": 1800,
        "runTime": 30,
        "type": "S",
        "flags": ["HD", "New"],
    }

    channel = {"channelNumber": "2.1"}

    result = gen._generate_programme(program, channel)
    assert "<programme" in result
    assert 'channel="2.1"' in result
    assert '<title lang="en">Test Show</title>' in result
    assert '<sub-title lang="en">Test Episode</sub-title>' in result
    assert '<category lang="en">sports</category>' in result
    assert "<video><quality>HDTV</quality></video>" in result
    assert "<new />" in result


def test_generate_programme_movie():
    """Test programme generation for movies"""
    gen = XMLTVGenerator("America/New_York")

    program = {
        "programId": "PR124",
        "title": "Test Movie",
        "subtitle": "",
        "startTime": "2023-05-23T20:00:00.000Z",
        "duration": 7200,
        "runTime": 120,
        "type": "M",
        "flags": [],
    }

    channel = {"channelNumber": "4.1"}

    result = gen._generate_programme(program, channel)
    assert '<category lang="en">movie</category>' in result
    assert "Test Movie" in result


def test_generate_full_xmltv():
    """Test full XMLTV generation"""
    gen = XMLTVGenerator("America/New_York")

    lineup_data = [
        {
            "channelNumber": "2.1",
            "stationId": 12345,
            "stationCallSign": "WABC",
            "logo": "/path/to/logo.png",
        }
    ]

    listings_by_day = [
        [
            [
                {
                    "programId": "PR123",
                    "title": "Test Show",
                    "subtitle": "Test Episode",
                    "startTime": "2023-05-23T20:00:00.000Z",
                    "duration": 1800,
                    "runTime": 30,
                    "type": "S",
                    "flags": ["HD"],
                }
            ]
        ]
    ]

    result = gen.generate(lineup_data, listings_by_day, "http://test.local")

    assert '<?xml version="1.0" encoding="UTF-8"?>' in result
    assert "<tv date=" in result
    assert 'source-info-name="tvtv2xmltv"' in result
    assert '<channel id="2.1">' in result
    assert "<programme" in result
    assert "Test Show" in result
    assert "</tv>" in result


def test_escape_special_characters():
    """Test that special XML characters are escaped"""
    gen = XMLTVGenerator()

    channel = {"channelNumber": "2.1", "stationCallSign": "Test & Station", "logo": "/logo.png"}

    result = gen._generate_channel(channel)
    assert "Test &amp; Station" in result

    program = {
        "programId": "PR123",
        "title": "Show & Movie",
        "subtitle": 'Episode with "quotes"',
        "startTime": "2023-05-23T20:00:00.000Z",
        "duration": 1800,
        "runTime": 30,
        "type": "M",
        "flags": [],
    }

    channel_simple = {"channelNumber": "2.1"}
    result = gen._generate_programme(program, channel_simple)
    assert "Show &amp; Movie" in result
    # The escape function escapes &, <, > but not quotes by default
    assert 'Episode with "quotes"' in result or "Episode with &quot;quotes&quot;" in result
