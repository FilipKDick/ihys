from typing import Any

from fastapi import APIRouter, HTTPException, status

from app.db.connection import db
from app.services.anime_actors import ensure_actor_data, ensure_anime_exists
from app.services.mal_api import MALApiError, MALApiService

router = APIRouter()


@router.get('/search')
async def search_anime(q: str = '') -> list[dict[str, Any]]:
    if len(q) < 2:
        return []
    mal_service = MALApiService()
    try:
        return await mal_service.search_anime(q)
    except MALApiError as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))


@router.get('/{mal_id}/actors')
async def get_anime_actors(mal_id: int) -> dict[str, Any]:
    try:
        anime = await ensure_anime_exists(mal_id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f'Could not fetch anime info: {str(e)}',
        )
    if not anime:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'Could not find or create anime with MAL ID {mal_id}',
        )

    try:
        await ensure_actor_data(anime['id'], mal_id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f'Could not fetch actor data: {str(e)}',
        )

    char_ids = [c['id'] for c in db.get_records('characters', {'anime_id': anime['id']})]
    char_actors = db.get_records_by_ids('character_actors', 'character_id', char_ids)
    actor_ids = list({ca['actor_id'] for ca in char_actors})
    actors = db.get_records_by_ids('actors', 'id', actor_ids)

    return {'anime': anime, 'actors': actors}
