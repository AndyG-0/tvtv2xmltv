"""
Tests for the configuration module
"""

import os
from tvtv2xmltv.config import Config


def test_config_defaults():
    """Test default configuration values"""
    # Clear environment variables
    for key in [
        "TVTV_TIMEZONE",
        "TVTV_LINEUP_ID",
        "TVTV_LINEUPS",
        "TVTV_DAYS",
        "TVTV_OUTPUT_FILE",
        "TVTV_UPDATE_INTERVAL",
        "TVTV_PORT",
        "TVTV_HOST",
    ]:
        os.environ.pop(key, None)

    config = Config()
    assert config.timezone == "America/New_York"
    # Default lineup should be available as both `lineup_id` and in `lineups` list
    assert config.lineup_id == "30236_OTA"
    assert config.lineups == ["30236_OTA"]
    assert config.days == 8
    assert config.output_file == "xmltv.xml"
    assert config.update_interval == 3600
    assert config.port == 8080
    assert config.host == "0.0.0.0"


def test_config_from_env():
    """Test configuration from environment variables"""
    os.environ["TVTV_TIMEZONE"] = "America/Los_Angeles"
    os.environ["TVTV_LINEUP_ID"] = "USA-TEST12345"
    os.environ["TVTV_DAYS"] = "5"
    os.environ["TVTV_OUTPUT_FILE"] = "test.xml"
    os.environ["TVTV_UPDATE_INTERVAL"] = "1800"
    os.environ["TVTV_PORT"] = "9090"
    os.environ["TVTV_HOST"] = "127.0.0.1"

    config = Config()
    assert config.timezone == "America/Los_Angeles"
    assert config.lineup_id == "USA-TEST12345"
    assert config.lineups == ["USA-TEST12345"]
    assert config.days == 5
    assert config.output_file == "test.xml"
    assert config.update_interval == 1800
    assert config.port == 9090
    assert config.host == "127.0.0.1"

    # Clean up
    for key in [
        "TVTV_TIMEZONE",
        "TVTV_LINEUP_ID",
        "TVTV_DAYS",
        "TVTV_OUTPUT_FILE",
        "TVTV_UPDATE_INTERVAL",
        "TVTV_PORT",
        "TVTV_HOST",
    ]:
        os.environ.pop(key, None)


def test_config_lineups_parsing():
    """Test parsing of comma-separated TVTV_LINEUPS"""
    os.environ["TVTV_LINEUPS"] = "USA-ONE, USA-TWO ,USA-THREE"
    config = Config()
    assert config.lineups == ["USA-ONE", "USA-TWO", "USA-THREE"]
    assert config.lineup_id == "USA-ONE"
    os.environ.pop("TVTV_LINEUPS", None)


def test_config_default_lineup_valid():
    """A TVTV_DEFAULT_LINEUP matching a configured lineup is accepted"""
    os.environ["TVTV_LINEUPS"] = "USA-ONE,USA-TWO"
    os.environ["TVTV_DEFAULT_LINEUP"] = "USA-TWO"
    config = Config()
    assert config.default_lineup == "USA-TWO"
    os.environ.pop("TVTV_LINEUPS", None)
    os.environ.pop("TVTV_DEFAULT_LINEUP", None)


def test_config_default_lineup_invalid():
    """A TVTV_DEFAULT_LINEUP not in the configured lineups is ignored"""
    os.environ["TVTV_LINEUPS"] = "USA-ONE,USA-TWO"
    os.environ["TVTV_DEFAULT_LINEUP"] = "USA-THREE"
    config = Config()
    assert config.default_lineup is None
    os.environ.pop("TVTV_LINEUPS", None)
    os.environ.pop("TVTV_DEFAULT_LINEUP", None)


def test_config_default_lineup_unset():
    """TVTV_DEFAULT_LINEUP is None when not set"""
    os.environ.pop("TVTV_DEFAULT_LINEUP", None)
    config = Config()
    assert config.default_lineup is None


def test_config_days_validation():
    """Test that days is capped at 14"""
    os.environ["TVTV_DAYS"] = "20"
    config = Config()
    assert config.days == 14

    os.environ["TVTV_DAYS"] = "0"
    config = Config()
    assert config.days == 1

    os.environ.pop("TVTV_DAYS", None)
