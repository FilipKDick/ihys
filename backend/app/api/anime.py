from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status

from app.db.connection import db
from app.services.anime_actors import ensure_actor_data, ensure_anime_exists
from app.services.auth import get_current_user_id
from app.services.mal_api import MALApiError, MALApiService

router = APIRouter()


@router.get('/search')
async def search_anime(
    q: str = '',
    user_id: Annotated[int, Depends(get_current_user_id)] = 0,
) -> list[dict[str, Any]]:
    if len(q) < 2:
        return []
    mal_service = MALApiService()
    try:
        return await mal_service.search_anime(q)
    except MALApiError as err:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail='Search failed',
        ) from err


@router.get('/{mal_id}/actors')
async def get_anime_actors(
    mal_id: int,
    user_id: Annotated[int, Depends(get_current_user_id)] = 0,
) -> dict[str, Any]:
    try:
        anime = await ensure_anime_exists(mal_id)
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail='Could not fetch anime info',
        ) from err
    if not anime:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'Anime with MAL ID {mal_id} not found',
        )

    try:
        await ensure_actor_data(anime['id'], mal_id)
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail='Could not fetch actor data',
        ) from err

    char_ids = [
        c['id'] for c in db.get_records('characters', {'anime_id': anime['id']})
    ]
    char_actors = db.get_records_by_ids('character_actors', 'character_id', char_ids)
    actor_ids = list({ca['actor_id'] for ca in char_actors})
    actors = db.get_records_by_ids('actors', 'id', actor_ids)

    return {'anime': anime, 'actors': actors}
