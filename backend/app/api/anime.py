from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status

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
