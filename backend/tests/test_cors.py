from unittest.mock import patch

from fastapi.testclient import TestClient


def test_cors_allows_configured_frontend_url():
    with patch.dict('os.environ', {'FRONTEND_URL': 'https://ihys.example.com'}):
        import importlib
        import app.core.config as config_module
        import app.main as main_module

        importlib.reload(config_module)
        importlib.reload(main_module)

        client = TestClient(main_module.app)
        response = client.get(
            '/',
            headers={'Origin': 'https://ihys.example.com'},
        )
        assert 'access-control-allow-origin' in response.headers
        assert response.headers['access-control-allow-origin'] == 'https://ihys.example.com'
