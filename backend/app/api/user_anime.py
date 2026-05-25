from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.db.connection import db
from app.serializers import (
    ActorOverlapResponse,
    SyncMalResponse,
    SyncMalStatsResponse,
    UserAnimeResponse,
)
from app.services.anime_actors import (
    ensure_actor_data,
    ensure_anime_exists,
    get_actor_overlap,
)
from app.services.auth import get_current_user_id
from app.services.mal_api import MALApiError, MALApiService
from app.services.watch_status import watch_status_rank

router = APIRouter()


@router.get('/anime', response_model=list[UserAnimeResponse])
async def get_user_anime_list(
    request: Request,
    user_id: Annotated[int, Depends(get_current_user_id)],
) -> list[UserAnimeResponse]:
    user_anime_records = db.get_records('user_anime', {'user_id': user_id}) or []

    entries = [
        UserAnimeResponse.from_records(user_anime, anime)
        for user_anime in user_anime_records
        if (anime := db.get_record_by_id('anime', user_anime['anime_id']))
    ]

    return sorted(
        entries,
        key=lambda entry: (
            watch_status_rank(entry.watch_status),
            entry.anime.name.casefold(),
        ),
    )


@router.post('/anime/sync', response_model=SyncMalResponse)
async def sync_mal_anime_list(
    request: Request,
    user_id: Annotated[int, Depends(get_current_user_id)],
) -> SyncMalResponse:
    mal_service = MALApiService()

    try:
        result = await mal_service.sync_user_anime_list(user_id)
    except MALApiError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f'MAL API error: {err!s}',
        ) from err

    return SyncMalResponse(
        message='Successfully synced anime list from MyAnimeList',
        stats=SyncMalStatsResponse.model_validate(result),
    )


@router.get('/anime/{mal_id}/overlap', response_model=list[ActorOverlapResponse])
async def get_anime_overlap(
    mal_id: int,
    request: Request,
    user_id: Annotated[int, Depends(get_current_user_id)],
) -> list[ActorOverlapResponse]:
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

    overlap = get_actor_overlap(mal_id, user_id)
    return [ActorOverlapResponse.model_validate(item) for item in overlap]
