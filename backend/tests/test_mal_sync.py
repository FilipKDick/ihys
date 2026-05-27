from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.schemas.mal import MalAnimeNode, MalListStatus, MalUserAnimeListEntry
from app.services.mal_api import MALApiService


@pytest.fixture
def anyio_backend() -> str:
    return 'asyncio'


@pytest.mark.anyio
async def test_get_user_access_token_accepts_database_datetime() -> None:
    service = MALApiService()
    future = datetime.now(timezone.utc) + timedelta(hours=1)
    db = MagicMock()
    db.get_record_by_id.return_value = {
        'id': 42,
        'encrypted_access_token': 'encrypted-token',
        'token_expires_at': future,
    }

    with (
        patch('app.services.mal_api.db', db),
        patch('app.services.mal_api.decrypt_token', return_value='access-token'),
    ):
        access_token = await service.get_user_access_token(42)

    assert access_token == 'access-token'


@pytest.mark.anyio
async def test_get_user_access_token_accepts_iso_string_with_z() -> None:
    service = MALApiService()
    future = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    db = MagicMock()
    db.get_record_by_id.return_value = {
        'id': 42,
        'encrypted_access_token': 'encrypted-token',
        'token_expires_at': future.replace('+00:00', 'Z'),
    }

    with (
        patch('app.services.mal_api.db', db),
        patch('app.services.mal_api.decrypt_token', return_value='access-token'),
    ):
        access_token = await service.get_user_access_token(42)

    assert access_token == 'access-token'


@pytest.mark.anyio
async def test_sync_skips_finished_anime_with_characters() -> None:
    service = MALApiService()
    service.fetch_user_anime_list = AsyncMock(
        return_value=[
            MalUserAnimeListEntry(
                node=MalAnimeNode(id=1, title='Already Scraped'),
                list_status=MalListStatus(status='completed'),
            ),
            MalUserAnimeListEntry(
                node=MalAnimeNode(id=2, title='Needs Actors'),
                list_status=MalListStatus(status='completed'),
            ),
        ],
    )

    db = MagicMock()
    db.get_records.side_effect = [
        [{'id': 10, 'name': 'Already Scraped', 'mal_id': 1}],
        [],
        [{'id': 11, 'name': 'Needs Actors', 'mal_id': 2}],
        [],
        [{'id': 100, 'name': 'Frieren', 'anime_id': 10}],
        [],
    ]
    db.insert_record.side_effect = [
        {'id': 1001, 'user_id': 42, 'anime_id': 10},
        {'id': 1002, 'user_id': 42, 'anime_id': 11},
    ]

    with (
        patch('app.services.mal_api.db', db),
        patch('app.services.mal_anime.db', db),
        patch(
            'app.services.mal_api.fetch_actor_data',
            new_callable=AsyncMock,
        ) as fetch_actor_data,
    ):
        result = await service.sync_user_anime_list(42)

    fetch_actor_data.assert_awaited_once_with(11, 2)
    assert result['actor_scraped'] == 1
    assert result['actor_skipped'] == 1
    assert result['actor_failed'] == 0


@pytest.mark.anyio
async def test_sync_refreshes_actor_data_for_currently_airing_anime() -> None:
    service = MALApiService()
    service.fetch_user_anime_list = AsyncMock(
        return_value=[
            MalUserAnimeListEntry(
                node=MalAnimeNode(
                    id=1,
                    title='Airing Show',
                    status='currently_airing',
                ),
                list_status=MalListStatus(status='watching'),
            ),
        ],
    )

    db = MagicMock()
    db.get_records.side_effect = [
        [{'id': 10, 'name': 'Airing Show', 'mal_id': 1, 'status': 'currently_airing'}],
        [],
        [{'id': 100, 'name': 'Hero', 'anime_id': 10}],
    ]
    db.insert_record.return_value = {'id': 1001, 'user_id': 42, 'anime_id': 10}

    with (
        patch('app.services.mal_api.db', db),
        patch('app.services.mal_anime.db', db),
        patch(
            'app.services.mal_api.fetch_actor_data',
            new_callable=AsyncMock,
        ) as fetch_actor_data,
    ):
        result = await service.sync_user_anime_list(42)

    fetch_actor_data.assert_awaited_once_with(10, 1)
    assert result['actor_scraped'] == 1
    assert result['actor_skipped'] == 0
    assert result['actor_failed'] == 0
