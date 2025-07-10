import secrets

from datetime import (
    datetime,
    timedelta,
    timezone,
)

import httpx

from fastapi import (
    APIRouter,
    Depends,
    Request,
    Response,
)
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.config import settings
from app.db.base import get_session
from app.db.models import User
from app.services.oauth import client
from app.services.security import encrypt_token

router = APIRouter()

CALLBACK_URL = f'{settings.BACKEND_URL}/api/auth/callback'


@router.get('/login')
async def login(request: Request) -> RedirectResponse:
    code_verifier = secrets.token_urlsafe(64)
    request.session['code_verifier'] = code_verifier

    mal_url = await client.get_authorization_url(
        CALLBACK_URL,
        scope=['read:users_animelist'],
        extras_params={
            'code_challenge_method': 'plain',
            'code_challenge': code_verifier,
        },
    )
    return RedirectResponse(url=mal_url)


@router.get('/callback')
async def callback(
    request: Request,
    response: Response,
    code: str,
    db: AsyncSession = Depends(get_session),  # noqa: B008
) -> Response:
    code_verifier = request.session.pop('code_verifier', None)
    if not code_verifier:
        return Response('Authorization error: No code verifier found.', status_code=400)

    token_data = await client.get_access_token(
        code,
        CALLBACK_URL,
        code_verifier=code_verifier,
    )
    access_token = token_data['access_token']
    expires_in = token_data['expires_in']

    expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

    async with httpx.AsyncClient() as user_client:
        headers = {'Authorization': f'Bearer {access_token}'}
        user_response = await user_client.get(
            'https://api.myanimelist.net/v2/users/@me',
            headers=headers,
        )
        user_info = user_response.json()

    mal_id = str(user_info['id'])
    mal_username = user_info['name']

    user_data = {
        'mal_id': mal_id,
        'mal_username': mal_username,
        'encrypted_access_token': encrypt_token(access_token),
        'encrypted_refresh_token': encrypt_token(token_data['refresh_token']),
        'token_expires_at': expires_at,
    }
    statement = select(User).where(User.mal_id == mal_id)
    result = await db.execute(statement)
    user = result.scalar_one_or_none()
    if user:
        user.sqlmodel_update(user_data)
    else:
        user = User.model_validate(user_data)
    db.add(user)

    await db.commit()
    await db.refresh(user)

    response = RedirectResponse(url=f'{settings.FRONTEND_URL}/dashboard')
    response.set_cookie(
        key='session_id',
        value=f'user-{user.id}',
        httponly=True,
        secure=False,  # Set to True in production
        samesite='lax',
    )
    return response
