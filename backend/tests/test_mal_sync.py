from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest

from app.services.mal_api import MALApiService


@pytest.fixture
def anyio_backend() -> str:
    return 'asyncio'


@pytest.mark.anyio
async def test_sync_fetches_actor_data_for_all_anime() -> None:
    service = MALApiService()
    service.fetch_user_anime_list = AsyncMock(
        return_value=[
            {
                'node': {'id': 1, 'title': 'Already Scraped'},
                'list_status': {'status': 'completed'},
            },
            {
                'node': {'id': 2, 'title': 'Needs Actors'},
                'list_status': {'status': 'completed'},
            },
        ],
    )

    db = MagicMock()
    db.get_records.side_effect = [
        [{'id': 10, 'name': 'Already Scraped', 'mal_id': 1}],
        [],
        [{'id': 11, 'name': 'Needs Actors', 'mal_id': 2}],
        [],
    ]
    db.insert_record.side_effect = [
        {'id': 1001, 'user_id': 42, 'anime_id': 10},
        {'id': 1002, 'user_id': 42, 'anime_id': 11},
    ]

    with (
        patch('app.services.mal_api.db', db),
        patch(
            'app.services.mal_api.fetch_actor_data',
            new_callable=AsyncMock,
        ) as fetch_actor_data,
    ):
        result = await service.sync_user_anime_list(42, auto_download=False)

    assert fetch_actor_data.await_count == 2
    fetch_actor_data.assert_has_awaits(
        [call(10, 1), call(11, 2)],
        any_order=True,
    )
    assert result['actor_scraped'] == 2
    assert result['actor_skipped'] == 0
    assert result['actor_failed'] == 0
