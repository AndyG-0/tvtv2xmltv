"""
Tests for the configuration module
"""

import os
from tvtv2xmltv.config import Config


def _clear_env():
    """Helper to clear all configuration env vars"""
    for key in [
        "GRACENOTE_TIMEZONE",
        "TVTV_TIMEZONE",
        "GRACENOTE_LINEUP_ID",
        "TVTV_LINEUP_ID",
        "GRACENOTE_LINEUPS",
        "TVTV_LINEUPS",
        "GRACENOTE_DEFAULT_LINEUP",
        "TVTV_DEFAULT_LINEUP",
        "GRACENOTE_DAYS",
        "TVTV_DAYS",
        "GRACENOTE_OUTPUT_FILE",
        "TVTV_OUTPUT_FILE",
        "GRACENOTE_UPDATE_INTERVAL",
        "TVTV_UPDATE_INTERVAL",
        "GRACENOTE_PORT",
        "TVTV_PORT",
        "GRACENOTE_HOST",
        "TVTV_HOST",
        "GRACENOTE_MOCK_MODE",
        "TVTV_MOCK_MODE",
        "GRACENOTE_STREAM_BASE_URL",
        "TVTV_STREAM_BASE_URL",
        "GRACENOTE_EXTERNAL_URL",
        "TVTV_EXTERNAL_URL",
    ]:
        os.environ.pop(key, None)


def test_config_defaults():
    """Test default configuration values (defaults to 85142 in Phoenix)"""
    _clear_env()

    config = Config()
    assert config.timezone == "America/Phoenix"
    # Default lineup should be 85142_OTA (Queen Creek, AZ home location)
    assert config.lineup_id == "85142_OTA"
    assert config.lineups == ["85142_OTA"]
    assert config.days == 8
    assert config.output_file == "xmltv.xml"
    assert config.update_interval == 3600
    assert config.port == 8080
    assert config.host == "0.0.0.0"


def test_config_from_gracenote_env():
    """Test configuration from GRACENOTE_* environment variables"""
    _clear_env()
    os.environ["GRACENOTE_TIMEZONE"] = "America/Phoenix"
    os.environ["GRACENOTE_LINEUP_ID"] = "85142_OTA"
    os.environ["GRACENOTE_DAYS"] = "5"
    os.environ["GRACENOTE_OUTPUT_FILE"] = "test.xml"
    os.environ["GRACENOTE_UPDATE_INTERVAL"] = "1800"
    os.environ["GRACENOTE_PORT"] = "9090"
    os.environ["GRACENOTE_HOST"] = "127.0.0.1"

    config = Config()
    assert config.timezone == "America/Phoenix"
    assert config.lineup_id == "85142_OTA"
    assert config.lineups == ["85142_OTA"]
    assert config.days == 5
    assert config.output_file == "test.xml"
    assert config.update_interval == 1800
    assert config.port == 9090
    assert config.host == "127.0.0.1"
    _clear_env()


def test_config_from_tvtv_legacy_env():
    """Test fallback configuration from legacy TVTV_* environment variables"""
    _clear_env()
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
    _clear_env()


def test_config_gracenote_precedence_over_tvtv():
    """GRACENOTE_* variables must take precedence over TVTV_* variables"""
    _clear_env()
    os.environ["GRACENOTE_TIMEZONE"] = "America/Phoenix"
    os.environ["TVTV_TIMEZONE"] = "America/New_York"
    os.environ["GRACENOTE_LINEUP_ID"] = "85142_OTA"
    os.environ["TVTV_LINEUP_ID"] = "30236_OTA"

    config = Config()
    assert config.timezone == "America/Phoenix"
    assert config.lineup_id == "85142_OTA"
    _clear_env()


def test_config_lineups_parsing():
    """Test parsing of comma-separated GRACENOTE_LINEUPS and TVTV_LINEUPS"""
    _clear_env()
    os.environ["GRACENOTE_LINEUPS"] = "85142_OTA, 85142_AZ02490 ,USA-THREE"
    config = Config()
    assert config.lineups == ["85142_OTA", "85142_AZ02490", "USA-THREE"]
    assert config.lineup_id == "85142_OTA"
    _clear_env()


def test_config_default_lineup_valid():
    """A default lineup matching a configured lineup is accepted"""
    _clear_env()
    os.environ["GRACENOTE_LINEUPS"] = "85142_OTA,85142_AZ02490"
    os.environ["GRACENOTE_DEFAULT_LINEUP"] = "85142_AZ02490"
    config = Config()
    assert config.default_lineup == "85142_AZ02490"
    _clear_env()


def test_config_default_lineup_invalid():
    """A default lineup not in configured lineups is ignored"""
    _clear_env()
    os.environ["GRACENOTE_LINEUPS"] = "85142_OTA,85142_AZ02490"
    os.environ["GRACENOTE_DEFAULT_LINEUP"] = "USA-THREE"
    config = Config()
    assert config.default_lineup is None
    _clear_env()


def test_config_default_lineup_unset():
    """default_lineup is None when not set"""
    _clear_env()
    config = Config()
    assert config.default_lineup is None


def test_config_days_validation():
    """Test that days is capped between 1 and 14"""
    _clear_env()
    os.environ["GRACENOTE_DAYS"] = "20"
    config = Config()
    assert config.days == 14

    os.environ["GRACENOTE_DAYS"] = "0"
    config = Config()
    assert config.days == 1
    _clear_env()
