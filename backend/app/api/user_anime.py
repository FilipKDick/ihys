import logging

from datetime import datetime, timezone
from typing import Any, Dict, List

import aiohttp

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.db.connection import db
from app.serializers import (
    AddAnimeRequest,
    UpdateAnimeRequest,
)
from app.services.anime_actors import (
    ensure_actor_data,
    ensure_anime_exists,
    get_actor_overlap,
)
from app.services.auth import get_current_user_id
from app.services.mal_api import MALApiError, MALApiService
from app.services.watch_status import watch_status_rank
from scrapers.animes import fetch_and_insert_anime_data

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get('/anime')
async def get_user_anime_list(
    request: Request, user_id: int = Depends(get_current_user_id),
) -> List[Dict[str, Any]]:
    try:
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
    except Exception:
        logger.exception('Failed to fetch anime list for user %s', user_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='Failed to fetch anime list',
        )


@router.post('/anime/sync')
async def sync_mal_anime_list(
    request: Request, user_id: int = Depends(get_current_user_id),
) -> Dict[str, Any]:
    mal_service = MALApiService()

    try:
        result = await mal_service.sync_user_anime_list(user_id)
        return {
            'message': 'Successfully synced anime list from MyAnimeList',
            'stats': result,
        }
    except MALApiError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f'MAL API error: {e!s}',
        )
    except Exception:
        logger.exception('Sync failed for user %s', user_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='Sync failed',
        )


@router.post('/anime')
async def add_anime_manually(
    anime_request: AddAnimeRequest,
    request: Request,
    user_id: int = Depends(get_current_user_id),
) -> Dict[str, Any]:
    try:
        existing_anime_records = db.get_records(
            'anime', {'name': anime_request.anime_name},
        )

        anime = None
        if existing_anime_records:
            anime = existing_anime_records[0]
        elif anime_request.anime_url:
            try:
                async with aiohttp.ClientSession() as session:
                    anime_model = await fetch_and_insert_anime_data(
                        session, anime_request.anime_url,
                    )
                    if anime_model and hasattr(anime_model, 'id') and anime_model.id:
                        anime = db.get_record_by_id('anime', anime_model.id)
            except Exception:
                logger.exception('Failed to scrape anime from URL for user %s', user_id)
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail='Failed to scrape anime from URL',
                )

        if not anime:
            anime_data = {
                'name': anime_request.anime_name,
                'created_at': datetime.now(timezone.utc).isoformat(),
            }
            anime = db.insert_record('anime', anime_data)
            if not anime:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail='Failed to create anime record',
                )

        existing_user_anime = db.get_records(
            'user_anime', {'user_id': user_id, 'anime_id': anime['id']},
        )

        if existing_user_anime:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='Anime already in your list',
            )

        user_anime_data = {
            'user_id': user_id,
            'anime_id': anime['id'],
            'watch_status': anime_request.watch_status,
            'is_synced_from_mal': False,
            'created_at': datetime.now(timezone.utc).isoformat(),
        }

        if anime_request.score is not None:
            user_anime_data['score'] = anime_request.score
        if anime_request.episodes_watched is not None:
            user_anime_data['episodes_watched'] = anime_request.episodes_watched
        if anime_request.start_date is not None:
            user_anime_data['start_date'] = anime_request.start_date
        if anime_request.finish_date is not None:
            user_anime_data['finish_date'] = anime_request.finish_date

        user_anime = db.insert_record('user_anime', user_anime_data)
        if not user_anime:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail='Failed to add anime to your list',
            )

        return {
            'message': 'Anime added to your list',
            'user_anime': {
                'id': user_anime['id'],
                'anime': anime,
                'watch_status': user_anime['watch_status'],
                'score': user_anime.get('score'),
                'episodes_watched': user_anime.get('episodes_watched'),
                'start_date': user_anime.get('start_date'),
                'finish_date': user_anime.get('finish_date'),
                'is_synced_from_mal': user_anime.get('is_synced_from_mal', False),
            },
        }
    except HTTPException:
        raise
    except Exception:
        logger.exception('Failed to add anime for user %s', user_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='Failed to add anime',
        )


@router.put('/anime/{user_anime_id}')
async def update_anime_status(
    user_anime_id: int,
    update_request: UpdateAnimeRequest,
    request: Request,
    user_id: int = Depends(get_current_user_id),
) -> Dict[str, Any]:
    try:
        user_anime = db.get_record_by_id('user_anime', user_anime_id)

        if not user_anime or user_anime['user_id'] != user_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail='Anime not found in your list',
            )

        update_data = {'updated_at': datetime.now(timezone.utc).isoformat()}

        if update_request.watch_status is not None:
            update_data['watch_status'] = update_request.watch_status
        if update_request.score is not None:
            update_data['score'] = update_request.score
        if update_request.episodes_watched is not None:
            update_data['episodes_watched'] = update_request.episodes_watched
        if update_request.start_date is not None:
            update_data['start_date'] = update_request.start_date
        if update_request.finish_date is not None:
            update_data['finish_date'] = update_request.finish_date

        updated_user_anime = db.update_record('user_anime', user_anime_id, update_data)
        if not updated_user_anime:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail='Failed to update anime status',
            )

        anime = db.get_record_by_id('anime', updated_user_anime['anime_id'])
        if not anime:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail='Anime data not found',
            )

        return {
            'message': 'Anime status updated',
            'user_anime': {
                'id': updated_user_anime['id'],
                'anime': anime,
                'watch_status': updated_user_anime['watch_status'],
                'score': updated_user_anime.get('score'),
                'episodes_watched': updated_user_anime.get('episodes_watched'),
                'start_date': updated_user_anime.get('start_date'),
                'finish_date': updated_user_anime.get('finish_date'),
                'is_synced_from_mal': updated_user_anime.get(
                    'is_synced_from_mal', False,
                ),
            },
        }
    except HTTPException:
        raise
    except Exception:
        logger.exception('Failed to update anime status for %s', user_anime_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='Failed to update anime',
        )


@router.delete('/anime/{user_anime_id}')
async def remove_anime_from_list(
    user_anime_id: int, request: Request, user_id: int = Depends(get_current_user_id),
) -> Dict[str, str]:
    try:
        user_anime = db.get_record_by_id('user_anime', user_anime_id)

        if not user_anime or user_anime['user_id'] != user_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail='Anime not found in your list',
            )

        db.delete_record('user_anime', user_anime_id)

        return {'message': 'Anime removed from your list'}
    except HTTPException:
        raise
    except Exception:
        logger.exception('Failed to remove anime %s for user', user_anime_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='Failed to remove anime',
        )


@router.get('/anime/{mal_id}/overlap')
async def get_anime_overlap(
    mal_id: int,
    request: Request,
    user_id: int = Depends(get_current_user_id),
) -> list[dict[str, Any]]:
    try:
        anime = await ensure_anime_exists(mal_id)
    except Exception:
        logger.exception('Failed to fetch anime info for MAL ID %s', mal_id)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail='Could not fetch anime info',
        )
    if not anime:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'Could not find or create anime with MAL ID {mal_id}',
        )

    try:
        await ensure_actor_data(anime['id'], mal_id)
    except Exception:
        logger.exception('Failed to fetch actor data for MAL ID %s', mal_id)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail='Could not fetch actor data',
        )

    return get_actor_overlap(mal_id, user_id)
