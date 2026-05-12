import logging

from datetime import datetime, timezone
from typing import Any

import httpx

from app.core.config import settings
from app.db.connection import db
from app.services.anime_actors import fetch_actor_data
from app.services.anime_download import AnimeDownloadService
from app.services.security import decrypt_token

logger = logging.getLogger(__name__)

_CURRENTLY_AIRING_STATUSES = {'currently_airing', 'currently airing'}


class MALApiError(Exception):
    pass


class MALApiService:
    BASE_URL = 'https://api.myanimelist.net/v2'

    async def get_user_access_token(self, user_id: int) -> str:
        user = db.get_record_by_id('users', user_id)

        if not user:
            raise MALApiError('User not found')

        token_expires_at_value = user['token_expires_at']
        if isinstance(token_expires_at_value, datetime):
            token_expires_at = token_expires_at_value
        else:
            token_expires_at = datetime.fromisoformat(
                token_expires_at_value.replace('Z', '+00:00'),
            )
        if token_expires_at.tzinfo is None:
            token_expires_at = token_expires_at.replace(tzinfo=timezone.utc)
        if token_expires_at <= datetime.now(timezone.utc):
            raise MALApiError('Token expired')

        return decrypt_token(user['encrypted_access_token'])

    async def fetch_user_anime_list(
        self,
        user_id: int,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        access_token = await self.get_user_access_token(user_id)

        anime_list = []
        offset = 0

        async with httpx.AsyncClient() as client:
            while True:
                headers = {'Authorization': f'Bearer {access_token}'}
                params = {
                    'fields': (
                        'list_status,num_episodes,start_date,end_date,synopsis,'
                        'mean,rank,popularity,genres,media_type,status'
                    ),
                    'limit': 1000
                    if limit is None
                    else min(limit - len(anime_list), 1000),
                    'offset': offset,
                }

                response = await client.get(
                    f'{self.BASE_URL}/users/@me/animelist',
                    headers=headers,
                    params=params,
                )

                if response.status_code != 200:
                    raise MALApiError(f'MAL API error: {response.status_code}')

                data = response.json()
                batch_anime = data.get('data', [])

                if not batch_anime:
                    break

                anime_list.extend(batch_anime)
                offset += len(batch_anime)

                if (
                    (limit is not None and len(anime_list) >= limit)
                    or len(batch_anime) < 1000
                ):
                    break

        return anime_list

    async def sync_user_anime_list(  # noqa: C901
        self,
        user_id: int,
        auto_download: bool = True,
    ) -> dict[str, int]:
        mal_anime_list = await self.fetch_user_anime_list(user_id)

        created_count = 0
        updated_count = 0
        downloaded_count = 0
        synced_anime: list[tuple[dict, int]] = []

        # Auto-download missing anime if enabled
        if auto_download:
            try:
                downloaded_count = (
                    await AnimeDownloadService.auto_download_missing_anime(
                        mal_anime_list,
                    )
                )
            except Exception as e:
                logger.warning(f'⚠️ Auto-download failed: {e!s}')

        for mal_anime_data in mal_anime_list:
            try:
                anime_data = mal_anime_data['node']
                list_status = mal_anime_data['list_status']

                mal_anime_id = anime_data['id']
                anime_title = anime_data['title']

                # Find anime in our database
                existing_anime = db.get_records('anime', {'mal_id': mal_anime_id})
                anime = None

                if existing_anime:
                    anime = existing_anime[0]
                else:
                    # If not found by MAL ID, try by name
                    name_match = db.get_records('anime', {'name': anime_title})
                    if name_match:
                        anime = name_match[0]
                        # Update with MAL ID
                        db.update_record('anime', anime['id'], {'mal_id': mal_anime_id})
                        anime['mal_id'] = mal_anime_id
                    else:
                        # Create anime record with basic info from MAL
                        anime_create_data = {
                            'name': anime_title,
                            'mal_id': mal_anime_id,
                            'episodes': str(anime_data.get('num_episodes', '')),
                            'status': anime_data.get('status', ''),
                            'synopsis': anime_data.get('synopsis', ''),
                            'score': str(anime_data.get('mean', '')),
                            'ranked': str(anime_data.get('rank', '')),
                            'popularity': str(anime_data.get('popularity', '')),
                            'genres': ','.join(
                                [
                                    genre['name']
                                    for genre in anime_data.get('genres', [])
                                ],
                            ),
                            'created_at': datetime.now(timezone.utc).isoformat(),
                        }
                        anime = db.insert_record('anime', anime_create_data)

                if not anime:
                    logger.error(f'❌ Failed to create/find anime: {anime_title}')
                    continue

                # Find existing user anime record
                existing_user_anime = db.get_records(
                    'user_anime',
                    {
                        'user_id': user_id,
                        'anime_id': anime['id'],
                    },
                )

                # Parse dates
                start_date = list_status.get('start_date')
                finish_date = list_status.get('finish_date')

                user_anime_data = {
                    'user_id': user_id,
                    'anime_id': anime['id'],
                    'mal_anime_id': mal_anime_id,
                    'watch_status': list_status['status'],
                    'is_synced_from_mal': True,
                    'updated_at': datetime.now(timezone.utc).isoformat(),
                }

                # Add optional fields only if they have values
                if list_status.get('score'):
                    user_anime_data['score'] = list_status['score']
                if list_status.get('num_episodes_watched'):
                    user_anime_data['episodes_watched'] = list_status[
                        'num_episodes_watched'
                    ]
                if start_date:
                    user_anime_data['start_date'] = start_date
                if finish_date:
                    user_anime_data['finish_date'] = finish_date

                if existing_user_anime:
                    db.update_record(
                        'user_anime',
                        existing_user_anime[0]['id'],
                        user_anime_data,
                    )
                    updated_count += 1
                else:
                    user_anime_data['created_at'] = datetime.now(
                        timezone.utc,
                    ).isoformat()
                    db.insert_record('user_anime', user_anime_data)
                    created_count += 1
                synced_anime.append((anime, mal_anime_id))

            except Exception as e:
                logger.error(f'❌ Error syncing anime {anime_title}: {e!s}')
                continue

        logger.info(
            f'🎯 Sync completed: {created_count} created, '
            f'{updated_count} updated, {downloaded_count} downloaded',
        )
        actor_stats = await self.sync_actor_data_for_anime(synced_anime)

        return {
            'created': created_count,
            'updated': updated_count,
            'downloaded': downloaded_count,
            'actor_scraped': actor_stats['scraped'],
            'actor_skipped': actor_stats['skipped'],
            'actor_failed': actor_stats['failed'],
            'total': len(mal_anime_list),
        }

    async def sync_actor_data_for_anime(
        self,
        synced_anime: list[tuple[dict, int]],
    ) -> dict[str, int]:
        scraped_count = 0
        skipped_count = 0
        failed_count = 0

        for anime, mal_anime_id in synced_anime:
            try:
                is_airing = (
                    (anime.get('status') or '').lower()
                    in _CURRENTLY_AIRING_STATUSES
                )
                if not is_airing:
                    existing = db.get_records('characters', {'anime_id': anime['id']})
                    if existing:
                        skipped_count += 1
                        continue
                await fetch_actor_data(anime['id'], mal_anime_id)
                scraped_count += 1
            except Exception as e:
                failed_count += 1
                logger.error(
                    f'❌ Error syncing actor data for {anime.get("name")}: {e!s}',
                )

        logger.info(
            f'🎭 Actor sync completed: {scraped_count} scraped, '
            f'{skipped_count} skipped, {failed_count} failed',
        )
        return {
            'scraped': scraped_count,
            'skipped': skipped_count,
            'failed': failed_count,
        }

    async def search_anime(self, query: str, limit: int = 10) -> list[dict]:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f'{self.BASE_URL}/anime',
                headers={'X-MAL-CLIENT-ID': settings.MAL_CLIENT_ID},
                params={
                    'q': query,
                    'limit': limit,
                    'fields': 'id,title,main_picture,start_date',
                },
            )
            if response.status_code != 200:
                raise MALApiError(f'MAL search failed: {response.status_code}')

            data = response.json()
            return [
                {
                    'mal_id': item['node']['id'],
                    'title': item['node']['title'],
                    'image': item['node'].get('main_picture', {}).get('medium'),
                    'year': item['node'].get('start_date', '')[:4]
                    if item['node'].get('start_date')
                    else None,
                }
                for item in data.get('data', [])
            ]
