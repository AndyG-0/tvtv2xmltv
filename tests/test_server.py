"""
Tests for the HTTP server
"""

import os

import pytest
from tvtv2xmltv.server import XMLTVServer
from tvtv2xmltv.config import Config


@pytest.fixture
def test_config():
    """Create a test configuration"""
    config = Config()
    config.lineup_id = "USA-TEST12345"
    config.lineups = ["USA-TEST12345"]
    config.days = 1
    config.output_file = "/tmp/test_server_xmltv.xml"
    config.port = 8888
    config.update_interval = 10
    return config


def test_server_initialization(test_config):
    """Test server initialization"""
    server = XMLTVServer(test_config)
    assert server.config == test_config
    assert server.app is not None
    assert server.last_update is None


def test_server_routes(test_config):
    """Test server routes are registered"""
    server = XMLTVServer(test_config)

    # Get the Flask app's URL map
    rules = [rule.rule for rule in server.app.url_map.iter_rules()]

    assert "/" in rules
    assert "/xmltv.xml" in rules
    assert "/health" in rules
    assert "/update" in rules


def test_health_endpoint_no_file(test_config):
    """Test health endpoint when file doesn't exist"""
    if os.path.exists(test_config.output_file):
        os.remove(test_config.output_file)

    server = XMLTVServer(test_config)
    client = server.app.test_client()

    response = client.get("/health")
    assert response.status_code == 200

    data = response.get_json()
    assert data["status"] == "healthy"
    assert data["files_exist"] is False
    assert "lineups" in data


def test_index_serves_xml_inline(test_config, tmp_path):
    """Index should serve XML inline with application/xml and inline disposition"""
    # Create a fake XML file
    xml_path = tmp_path / "test_epg.xml"
    xml_content = "<?xml version='1.0' encoding='UTF-8'?>\n<tv></tv>\n"
    xml_path.write_text(xml_content, encoding="utf-8")

    test_config.output_file = str(xml_path)
    server = XMLTVServer(test_config)

    # Map the lineup to the test file
    server.lineup_files[test_config.lineups[0]] = str(xml_path)

    client = server.app.test_client()

    response = client.get("/")
    assert response.status_code == 200
    # Content type should be application/xml with utf-8 charset
    assert response.headers.get("Content-Type", "").startswith("application/xml")
    # Content disposition should be inline (not attachment)
    cd = response.headers.get("Content-Disposition", "")
    assert "inline" in cd
    # Body should contain the XML declaration and content
    assert response.get_data(as_text=True).startswith("<?xml")
