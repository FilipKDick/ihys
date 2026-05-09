from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app, raise_server_exceptions=False)

MOCK_USER = {'id': 1, 'mal_username': 'testuser'}


def authed_get(path):
    with patch('app.services.auth.get_current_user', return_value=MOCK_USER):
        return client.get(path, cookies={'session_id': 'tok'})


def authed_post(path, json=None):
    with patch('app.services.auth.get_current_user', return_value=MOCK_USER):
        return client.post(path, json=json or {}, cookies={'session_id': 'tok'})


def test_anime_list_error_does_not_leak_exception():
    with patch('app.api.user_anime.db') as mock_db:
        mock_db.get_records.side_effect = Exception('secret internal db error xyz')
        response = authed_get('/api/user/anime')
    assert response.status_code == 500
    assert 'secret internal db error xyz' not in response.text


def test_sync_error_does_not_leak_exception():
    with patch('app.api.user_anime.MALApiService') as mock_svc:
        instance = MagicMock()
        instance.sync_user_anime_list.side_effect = Exception('secret internal sync error xyz')
        mock_svc.return_value = instance
        response = authed_post('/api/user/anime/sync')
    assert response.status_code == 500
    assert 'secret internal sync error xyz' not in response.text
