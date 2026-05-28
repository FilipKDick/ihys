import logging

from datetime import datetime, timezone

import httpx

from pydantic import ValidationError

from app.core.config import settings
from app.db.connection import db
from app.db.models import Anime
from app.schemas.mal import MalUserAnimeListEntry
from app.services.anime_actors import fetch_actor_data
from app.services.mal_anime import MALApiError, ensure_anime_record
from app.services.security import decrypt_token

logger = logging.getLogger(__name__)

# MAL API returns 'currently_airing'; HTML scraper returns 'Currently Airing'
_CURRENTLY_AIRING_STATUSES = {'currently_airing', 'currently airing'}


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
    ) -> list[MalUserAnimeListEntry]:
        access_token = await self.get_user_access_token(user_id)

        anime_list: list[MalUserAnimeListEntry] = []
        offset = 0

        async with httpx.AsyncClient() as client:
            while True:
                headers = {'Authorization': f'Bearer {access_token}'}
                params = {
                    'fields': (
                        'list_status,num_episodes,start_date,end_date,synopsis,'
                        'mean,rank,popularity,genres,media_type,status'
                    ),
                    'limit': 1000,
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

                for item in batch_anime:
                    try:
                        anime_list.append(MalUserAnimeListEntry.model_validate(item))
                    except ValidationError as err:
                        raise MALApiError(
                            f'Invalid MAL animelist entry: {err!s}',
                        ) from err
                offset += len(batch_anime)

        return anime_list

    async def sync_user_anime_list(
        self,
        user_id: int,
    ) -> dict[str, int]:
        mal_anime_list = await self.fetch_user_anime_list(user_id)

        created_count = 0
        updated_count = 0
        synced_anime: list[Anime] = []

        for entry in mal_anime_list:
            anime = ensure_anime_record(entry.node)

            # todo get_or_update on db level
            existing_user_anime = db.get_records(
                'user_anime',
                {
                    'user_id': user_id,
                    'anime_id': anime.id,
                },
            )

            if existing_user_anime:
                db.update_record(
                    'user_anime',
                    existing_user_anime[0]['id'],
                    entry.to_user_anime_upsert_data(
                        user_id=user_id,
                        anime_id=anime.id,
                    ),
                )
                updated_count += 1
            else:
                db.insert_record(
                    'user_anime',
                    entry.to_user_anime_insert_data(
                        user_id=user_id,
                        anime_id=anime.id,
                    ),
                )
                created_count += 1
            synced_anime.append(anime)

        logger.info(
            f'🎯 Sync completed: {created_count} created, {updated_count} updated',
        )
        actor_stats = await self.sync_actor_data_for_anime(synced_anime)

        return {
            'created': created_count,
            'updated': updated_count,
            'actor_scraped': actor_stats['scraped'],
            'actor_skipped': actor_stats['skipped'],
            'actor_failed': actor_stats['failed'],
            'total': len(mal_anime_list),
        }

    async def sync_actor_data_for_anime(
        self,
        synced_anime: list[Anime],
    ) -> dict[str, int]:
        scraped_count = 0
        skipped_count = 0
        failed_count = 0

        for anime in synced_anime:
            try:
                raw_status = anime.status
                is_airing = (raw_status or '').lower() in _CURRENTLY_AIRING_STATUSES
                logger.info(
                    f'🎬 {anime.name}: status={raw_status!r} is_airing={is_airing}',
                )
                if not is_airing:
                    existing = db.get_records(
                        'characters', {'anime_id': anime.id}, limit=1,
                    )
                    if existing:
                        skipped_count += 1
                        continue
                await fetch_actor_data(anime.id, anime.mal_id)
                scraped_count += 1
            except Exception as e:
                failed_count += 1
                logger.error(
                    f'❌ Error syncing actor data for {anime.name}: {e!s}',
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
