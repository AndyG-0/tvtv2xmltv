"""
Tests for the HTTP server
"""

import os
import time

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
    config.default_lineup = None
    return config


@pytest.fixture
def multi_lineup_config(tmp_path):
    """Create a test configuration with multiple lineups"""
    config = Config()
    config.lineup_id = "USA-ONE"
    config.lineups = ["USA-ONE", "USA-TWO"]
    config.days = 1
    config.output_file = str(tmp_path / "xmltv.xml")
    config.port = 8888
    config.update_interval = 10
    config.default_lineup = None
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
    assert "/stats" in rules
    assert "/update" in rules
    assert "/list" in rules
    assert "/dashboard" in rules
    assert "/set-default/<lineup_id>" in rules


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
    assert "stats" in data


def test_stats_endpoint(multi_lineup_config):
    """Test /stats endpoint returns feed statistics"""
    server = XMLTVServer(multi_lineup_config)
    server.converter.stats = {
        "USA-ONE": {
            "channels": 5,
            "days": 7,
            "programs": 150,
            "lineup_id": "USA-ONE",
        }
    }
    client = server.app.test_client()

    response = client.get("/stats")
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "healthy"
    assert "USA-ONE" in data["stats"]
    assert data["stats"]["USA-ONE"]["channels"] == 5
    assert data["stats"]["USA-ONE"]["days"] == 7
    assert data["stats"]["USA-ONE"]["programs"] == 150


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


def test_root_lists_lineups_when_no_default(multi_lineup_config):
    """With no default set, '/' should show the listing (today's behavior)"""
    server = XMLTVServer(multi_lineup_config)
    client = server.app.test_client()

    response = client.get("/")
    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "USA-ONE.xml" in body
    assert "USA-TWO.xml" in body


def test_list_endpoint_always_shows_listing(multi_lineup_config, tmp_path):
    """'/list' should show the listing even when a default is set"""
    xml_path = tmp_path / "one.xml"
    xml_path.write_text("<?xml version='1.0'?><tv></tv>", encoding="utf-8")

    multi_lineup_config.default_lineup = "USA-ONE"
    server = XMLTVServer(multi_lineup_config)
    server.lineup_files["USA-ONE"] = str(xml_path)
    client = server.app.test_client()

    response = client.get("/list")
    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "USA-ONE.xml" in body
    assert "USA-TWO.xml" in body


def test_root_serves_env_default_lineup(multi_lineup_config, tmp_path):
    """With TVTV_DEFAULT_LINEUP-equivalent config set, '/' serves that file"""
    xml_path = tmp_path / "one.xml"
    xml_path.write_text("<?xml version='1.0'?><tv></tv>", encoding="utf-8")

    multi_lineup_config.default_lineup = "USA-ONE"
    server = XMLTVServer(multi_lineup_config)
    server.lineup_files["USA-ONE"] = str(xml_path)
    client = server.app.test_client()

    response = client.get("/")
    assert response.status_code == 200
    assert response.headers.get("Content-Type", "").startswith("application/xml")


def test_set_default_persists_and_serves(multi_lineup_config, tmp_path):
    """Picking a default via /set-default should persist and affect '/'"""
    xml_path = tmp_path / "two.xml"
    xml_path.write_text("<?xml version='1.0'?><tv></tv>", encoding="utf-8")

    server = XMLTVServer(multi_lineup_config)
    server.lineup_files["USA-TWO"] = str(xml_path)
    client = server.app.test_client()

    response = client.get("/set-default/USA-TWO")
    assert response.status_code == 302
    assert response.headers["Location"] == "/"
    assert os.path.exists(server._default_lineup_state_path())

    response = client.get("/")
    assert response.status_code == 200
    assert response.headers.get("Content-Type", "").startswith("application/xml")

    # A fresh server instance should pick up the persisted default
    server2 = XMLTVServer(multi_lineup_config)
    assert server2.runtime_default_lineup == "USA-TWO"


def test_set_default_invalid_lineup_404(multi_lineup_config):
    """Picking an unconfigured lineup as default should 404"""
    server = XMLTVServer(multi_lineup_config)
    client = server.app.test_client()

    response = client.get("/set-default/NOT-A-LINEUP")
    assert response.status_code == 404


def test_update_loop_has_no_initial_call(test_config, monkeypatch):
    """_update_loop should not call _update_xmltv before its first sleep

    (the initial fetch now happens once, synchronously, in run())
    """
    server = XMLTVServer(test_config)
    server.config.update_interval = 0
    calls = []
    monkeypatch.setattr(server, "_update_xmltv", lambda: calls.append(True))

    server.running = True
    sleep_calls = []

    def fake_sleep(_seconds):
        sleep_calls.append(True)
        if len(sleep_calls) >= 2:
            server.running = False

    monkeypatch.setattr(time, "sleep", fake_sleep)
    server._update_loop()

    assert calls == [True]


def test_list_endpoint_shows_feed_stats(multi_lineup_config):
    """'/list' should render feed statistics and reload button when available"""
    server = XMLTVServer(multi_lineup_config)
    server.converter.stats = {
        "USA-ONE": {
            "channels": 6,
            "days": 8,
            "programs": 120,
            "lineup_id": "USA-ONE",
            "start_date": "2026-08-22",
            "end_date": "2026-08-29",
            "date_range": "2026-08-22 to 2026-08-29",
            "file_size_human": "1.2 MB",
            "last_refreshed": "2026-08-22T10:00:00+00:00",
        },
        "USA-TWO": {
            "channels": 1,
            "days": 1,
            "programs": 1,
            "lineup_id": "USA-TWO",
            "start_date": "2026-08-22",
            "end_date": "2026-08-22",
            "date_range": "2026-08-22",
            "file_size_human": "50 KB",
            "last_refreshed": "2026-08-22T10:00:00+00:00",
        },
    }
    client = server.app.test_client()

    response = client.get("/list")
    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "6 channels, 8 days of guide (120 programs)" in body
    assert "1 channel, 1 day of guide (1 program)" in body
    assert "2026-08-22 to 2026-08-29" in body
    assert "Reload Feeds" in body
    assert 'id="reload-btn"' in body
    assert "Last Refreshed" in body


def test_list_endpoint_refreshed_banner(multi_lineup_config):
    """'/list?refreshed=1' should render the success banner"""
    server = XMLTVServer(multi_lineup_config)
    client = server.app.test_client()

    response = client.get("/list?refreshed=1")
    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "Feeds refreshed successfully!" in body


def test_dashboard_alias(multi_lineup_config):
    """'/dashboard' should render the same listing as '/list'"""
    server = XMLTVServer(multi_lineup_config)
    client = server.app.test_client()

    response = client.get("/dashboard")
    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "Available XMLTV Lineups" in body
    assert "Reload Feeds" in body


def test_update_endpoint_get_json(test_config, monkeypatch):
    """GET /update should return JSON update status"""
    server = XMLTVServer(test_config)
    monkeypatch.setattr(server.converter, "save_to_file", lambda: [test_config.output_file])
    client = server.app.test_client()

    response = client.get("/update")
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "updated"
    assert data["last_update"] is not None


def test_update_endpoint_post_json(test_config, monkeypatch):
    """POST /update with JSON accept should return JSON"""
    server = XMLTVServer(test_config)
    monkeypatch.setattr(server.converter, "save_to_file", lambda: [test_config.output_file])
    client = server.app.test_client()

    response = client.post("/update", headers={"Accept": "application/json"})
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "updated"


def test_update_endpoint_post_form_redirects(test_config, monkeypatch):
    """POST /update from standard form should redirect to /list?refreshed=1"""
    server = XMLTVServer(test_config)
    monkeypatch.setattr(server.converter, "save_to_file", lambda: [test_config.output_file])
    client = server.app.test_client()

    response = client.post("/update", headers={"Accept": "text/html"})
    assert response.status_code == 302
    assert response.headers["Location"] == "/list?refreshed=1"


def test_update_xmltv_logging_with_stats(test_config, monkeypatch, capsys):
    """_update_xmltv should log feed stats for generated files"""
    server = XMLTVServer(test_config)
    monkeypatch.setattr(server.converter, "save_to_file", lambda: [test_config.output_file])
    server.converter.stats[test_config.lineups[0]] = {
        "channels": 10,
        "days": 5,
        "programs": 200,
        "lineup_id": test_config.lineups[0],
    }

    server._update_xmltv()
    captured = capsys.readouterr()
    assert "10 channels" in captured.out
    assert "5 days of guide" in captured.out
    assert "200 programs" in captured.out
    assert server.converter.stats[test_config.lineups[0]]["last_refreshed"] is not None
