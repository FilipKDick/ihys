from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app, raise_server_exceptions=False)


def test_search_requires_auth():
    response = client.get('/api/anime/search?q=naruto')
    assert response.status_code == 401


def test_search_works_when_authenticated():
    mock_user = {'id': 1, 'mal_username': 'testuser'}
    with patch('app.services.auth.get_current_user', return_value=mock_user):
        with patch(
            'app.services.mal_api.MALApiService.search_anime',
            new_callable=AsyncMock,
            return_value=[],
        ):
            response = client.get(
                '/api/anime/search?q=naruto',
                cookies={'session_id': 'fake-token'},
            )
    assert response.status_code == 200
