from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.serializers import AnimeSearchResultResponse
from app.services.auth import get_current_user_id
from app.services.mal_api import MALApiError, MALApiService

router = APIRouter()


@router.get('/search', response_model=list[AnimeSearchResultResponse])
async def search_anime(
    q: str = '',
    user_id: Annotated[int, Depends(get_current_user_id)] = 0,
) -> list[AnimeSearchResultResponse]:
    if len(q) < 2:
        return []
    mal_service = MALApiService()
    try:
        results = await mal_service.search_anime(q)
    except MALApiError as err:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail='Search failed',
        ) from err
    return [AnimeSearchResultResponse.model_validate(item) for item in results]
