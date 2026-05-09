import secrets

from datetime import datetime, timedelta, timezone
from typing import Annotated

import httpx

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import RedirectResponse

from app.core.config import settings
from app.db.connection import db
from app.services.auth import create_session, delete_session, get_current_user
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
async def callback(request: Request, code: str) -> Response:
    code_verifier = request.session.pop('code_verifier', None)
    if not code_verifier:
        return Response('Authorization error: No code verifier found.', status_code=400)

    token_data = await client.get_access_token(
        code, CALLBACK_URL, code_verifier=code_verifier,
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
        if user_response.status_code != 200:
            return Response(
                f'Failed to fetch MAL user info: {user_response.status_code}',
                status_code=502,
            )
        user_info = user_response.json()

    mal_id = str(user_info['id'])
    mal_username = user_info['name']

    user_data = {
        'mal_id': mal_id,
        'mal_username': mal_username,
        'encrypted_access_token': encrypt_token(access_token),
        'encrypted_refresh_token': encrypt_token(token_data['refresh_token']),
        'token_expires_at': expires_at.isoformat(),
    }

    user = db.upsert_record('users', user_data, conflict_columns=['mal_id'])
    if not user:
        return Response('Failed to persist user record.', status_code=500)

    token = create_session(user['id'])

    response = RedirectResponse(url=f'{settings.FRONTEND_URL}/dashboard')
    response.set_cookie(
        key='session_id',
        value=token,
        httponly=True,
        secure=not settings.DEBUG,
        samesite='lax',
        max_age=60 * 60 * 24 * 30,
    )
    return response


@router.post('/logout')
async def logout(request: Request, response: Response) -> dict:
    token = request.cookies.get('session_id')
    if token:
        delete_session(token)
    response.delete_cookie('session_id')
    return {'ok': True}


@router.get('/me')
async def get_me(user: Annotated[dict, Depends(get_current_user)]) -> dict:
    return {'id': user['id'], 'username': user['mal_username']}
