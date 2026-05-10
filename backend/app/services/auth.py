import secrets

from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import HTTPException, Request, status

from app.db.connection import db, get_pool

SESSION_DURATION_DAYS = 30


class AuthenticationError(Exception):
    pass


def create_session(user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(days=SESSION_DURATION_DAYS)
    db.insert_record('sessions', {
        'token': token,
        'user_id': user_id,
        'expires_at': expires_at.isoformat(),
    })
    return token


def delete_session(token: str) -> None:
    with get_pool().connection() as conn:
        with conn.cursor() as cur:
            cur.execute('DELETE FROM sessions WHERE token = %s', (token,))


def get_current_user(request: Request) -> dict[str, Any]:
    token = request.cookies.get('session_id')
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail='Not authenticated',
        )

    rows = db.get_records('sessions', {'token': token})
    if not rows:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid session',
        )

    session = rows[0]
    expires_at_value = session['expires_at']
    if isinstance(expires_at_value, datetime):
        expires_at = expires_at_value
    else:
        expires_at = datetime.fromisoformat(expires_at_value)
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if datetime.now(timezone.utc) > expires_at:
        delete_session(token)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail='Session expired',
        )

    user = db.get_record_by_id('users', session['user_id'])
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail='User not found',
        )

    return user


def get_current_user_id(request: Request) -> int:
    return get_current_user(request)['id']
