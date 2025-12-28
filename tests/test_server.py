"""
Tests for the HTTP server
"""
import pytest
import os
import time
from tvtv2xmltv.server import XMLTVServer
from tvtv2xmltv.config import Config


@pytest.fixture
def test_config():
    """Create a test configuration"""
    config = Config()
    config.lineup_id = 'USA-TEST12345'
    config.days = 1
    config.output_file = '/tmp/test_server_xmltv.xml'
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
    
    assert '/' in rules
    assert '/xmltv.xml' in rules
    assert '/health' in rules
    assert '/update' in rules


def test_health_endpoint_no_file(test_config):
    """Test health endpoint when file doesn't exist"""
    if os.path.exists(test_config.output_file):
        os.remove(test_config.output_file)
    
    server = XMLTVServer(test_config)
    client = server.app.test_client()
    
    response = client.get('/health')
    assert response.status_code == 200
    
    data = response.get_json()
    assert data['status'] == 'healthy'
    assert data['file_exists'] is False
