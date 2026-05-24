from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.db.connection import db
from app.services.anime_actors import (
    ensure_actor_data,
    ensure_anime_exists,
    get_actor_overlap,
)
from app.services.auth import get_current_user_id
from app.services.mal_api import MALApiError, MALApiService
from app.services.watch_status import watch_status_rank

router = APIRouter()


@router.get('/anime')
async def get_user_anime_list(
    request: Request, user_id: int = Depends(get_current_user_id),
) -> List[Dict[str, Any]]:
    user_anime_records = db.get_records('user_anime', {'user_id': user_id}) or []

    result = []
    for user_anime in user_anime_records:
        anime = db.get_record_by_id('anime', user_anime['anime_id'])
        if anime:
            result.append(
                {
                    'id': user_anime['id'],
                    'anime': anime,
                    'watch_status': user_anime['watch_status'],
                    'score': user_anime.get('score'),
                    'episodes_watched': user_anime.get('episodes_watched'),
                    'start_date': user_anime.get('start_date'),
                    'finish_date': user_anime.get('finish_date'),
                    'is_synced_from_mal': user_anime.get(
                        'is_synced_from_mal', False,
                    ),
                },
            )

    return sorted(
        result,
        key=lambda entry: (
            watch_status_rank(entry['watch_status']),
            entry['anime'].get('name', '').casefold(),
        ),
    )


@router.post('/anime/sync')
async def sync_mal_anime_list(
    request: Request, user_id: int = Depends(get_current_user_id),
) -> Dict[str, Any]:
    mal_service = MALApiService()

    try:
        result = await mal_service.sync_user_anime_list(user_id)
    except MALApiError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f'MAL API error: {err!s}',
        ) from err

    return {
        'message': 'Successfully synced anime list from MyAnimeList',
        'stats': result,
    }


@router.get('/anime/{mal_id}/overlap')
async def get_anime_overlap(
    mal_id: int,
    request: Request,
    user_id: int = Depends(get_current_user_id),
) -> list[dict[str, Any]]:
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
            detail=f'Could not find or create anime with MAL ID {mal_id}',
        )

    try:
        await ensure_actor_data(anime['id'], mal_id)
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail='Could not fetch actor data',
        ) from err

    return get_actor_overlap(mal_id, user_id)
