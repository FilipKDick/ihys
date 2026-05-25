from unittest.mock import MagicMock, patch

import pytest

from app.api.user_anime import get_user_anime_list


@pytest.fixture
def anyio_backend() -> str:
    return 'asyncio'


@pytest.mark.anyio
async def test_user_anime_list_sorts_by_watch_status_then_name() -> None:
    db = MagicMock()
    db.get_records.return_value = [
        {'id': 1, 'anime_id': 10, 'watch_status': 'plan_to_watch'},
        {'id': 2, 'anime_id': 11, 'watch_status': 'watching'},
        {'id': 3, 'anime_id': 12, 'watch_status': 'dropped'},
        {'id': 4, 'anime_id': 13, 'watch_status': 'completed'},
    ]
    db.get_record_by_id.side_effect = [
        {'id': 10, 'name': 'Planned Show', 'mal_id': 10},
        {'id': 11, 'name': 'Watching Show', 'mal_id': 11},
        {'id': 12, 'name': 'Dropped Show', 'mal_id': 12},
        {'id': 13, 'name': 'Completed Show', 'mal_id': 13},
    ]

    with patch('app.api.user_anime.db', db):
        result = await get_user_anime_list(MagicMock(), user_id=42)

    assert [entry.watch_status for entry in result] == [
        'completed',
        'watching',
        'plan_to_watch',
        'dropped',
    ]
    assert [entry.anime.name for entry in result] == [
        'Completed Show',
        'Watching Show',
        'Planned Show',
        'Dropped Show',
    ]
