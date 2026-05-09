# Secure Session Tokens Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the guessable `session_id=user-{id}` cookie with a random opaque token stored in a `sessions` DB table, so session IDs cannot be forged by knowing a user's ID.

**Architecture:** Add a `sessions` table (token → user_id, expires_at). On login, generate a `secrets.token_urlsafe(32)` token, insert it into `sessions`, set it as the cookie value. On each request, look up the token in `sessions` to get the user. On logout, delete the session row. `services/auth.py` is the only file that changes its logic; `api/auth.py` changes only cookie writing and adds a logout endpoint.

**Tech Stack:** Python `secrets`, psycopg3 (existing `db.*` layer), FastAPI, existing cookie infrastructure.

---

### Task 1: Add sessions table migration

**Files:**
- Create: `supabase/migrations/20260510120000_add_sessions.sql`

- [ ] **Step 1: Write the migration file**

```sql
create table if not exists public.sessions (
    token text primary key,
    user_id bigint not null references public.users(id) on delete cascade,
    created_at timestamptz not null default now(),
    expires_at timestamptz not null
);

create index if not exists sessions_user_id_idx on public.sessions(user_id);
```

- [ ] **Step 2: Apply the migration to the running postgres container**

```bash
docker compose exec postgres psql -U ihys -d ihys -f /dev/stdin < supabase/migrations/20260510120000_add_sessions.sql
```

Expected: `CREATE TABLE` and `CREATE INDEX` with no errors.

- [ ] **Step 3: Verify table exists**

```bash
docker compose exec postgres psql -U ihys -d ihys -c "\d public.sessions"
```

Expected: shows columns `token`, `user_id`, `created_at`, `expires_at`.

- [ ] **Step 4: Commit**

```bash
git add supabase/migrations/20260510120000_add_sessions.sql
git commit -m "feat: add sessions table for secure token-based auth"
```

---

### Task 2: Rewrite services/auth.py

**Files:**
- Modify: `backend/app/services/auth.py`
- Test: `backend/tests/test_auth_service.py` (create)

- [ ] **Step 1: Write failing tests**

Create `backend/tests/test_auth_service.py`:

```python
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from app.services.auth import create_session, get_current_user, delete_session


def make_db(get_records=None, insert=None, delete=None):
    db = MagicMock()
    db.get_records.return_value = get_records or []
    db.insert_record.return_value = insert
    db.delete_record.return_value = delete
    return db


def test_create_session_inserts_and_returns_token():
    db = make_db(insert={'token': 'abc', 'user_id': 1, 'expires_at': 'x', 'created_at': 'y'})
    with patch('app.services.auth.db', db):
        token = create_session(user_id=1)
    assert isinstance(token, str)
    assert len(token) > 20
    call_args = db.insert_record.call_args
    assert call_args[0][0] == 'sessions'
    data = call_args[0][1]
    assert data['user_id'] == 1
    assert data['token'] == token


def test_get_current_user_returns_user_for_valid_token():
    future = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    db = MagicMock()
    db.get_records.return_value = [{'token': 'tok', 'user_id': 7, 'expires_at': future}]
    db.get_record_by_id.return_value = {'id': 7, 'mal_username': 'testuser'}

    from fastapi import Request
    request = MagicMock(spec=Request)
    request.cookies = {'session_id': 'tok'}

    with patch('app.services.auth.db', db):
        user = get_current_user(request)

    assert user['id'] == 7


def test_get_current_user_raises_401_for_missing_cookie():
    from fastapi import HTTPException, Request
    request = MagicMock(spec=Request)
    request.cookies = {}

    with pytest.raises(HTTPException) as exc:
        get_current_user(request)
    assert exc.value.status_code == 401


def test_get_current_user_raises_401_for_unknown_token():
    from fastapi import HTTPException, Request
    db = MagicMock()
    db.get_records.return_value = []

    request = MagicMock(spec=Request)
    request.cookies = {'session_id': 'unknown-token'}

    with patch('app.services.auth.db', db):
        with pytest.raises(HTTPException) as exc:
            get_current_user(request)
    assert exc.value.status_code == 401


def test_get_current_user_raises_401_for_expired_token():
    from fastapi import HTTPException, Request
    past = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    db = MagicMock()
    db.get_records.return_value = [{'token': 'tok', 'user_id': 7, 'expires_at': past}]

    request = MagicMock(spec=Request)
    request.cookies = {'session_id': 'tok'}

    with patch('app.services.auth.db', db):
        with pytest.raises(HTTPException) as exc:
            get_current_user(request)
    assert exc.value.status_code == 401


def test_delete_session_removes_row():
    db = MagicMock()
    db.get_records.return_value = [{'token': 'tok', 'user_id': 5}]

    with patch('app.services.auth.db', db):
        delete_session('tok')

    db.get_records.assert_called_once_with('sessions', {'token': 'tok'})
    db.delete_record.assert_called_once_with('sessions', 'tok')
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
docker compose exec backend pytest tests/test_auth_service.py -v
```

Expected: import errors or assertion errors — `create_session` and `delete_session` don't exist yet.

- [ ] **Step 3: Rewrite backend/app/services/auth.py**

```python
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import HTTPException, Request, status

from app.db.connection import db

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
    rows = db.get_records('sessions', {'token': token})
    if rows:
        db.delete_record('sessions', token)


def get_current_user(request: Request) -> dict[str, Any]:
    token = request.cookies.get('session_id')
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Not authenticated')

    rows = db.get_records('sessions', {'token': token})
    if not rows:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid session')

    session = rows[0]
    expires_at = datetime.fromisoformat(session['expires_at'])
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if datetime.now(timezone.utc) > expires_at:
        delete_session(token)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Session expired')

    user = db.get_record_by_id('users', session['user_id'])
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='User not found')

    return user


def get_current_user_id(request: Request) -> int:
    return get_current_user(request)['id']
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
docker compose exec backend pytest tests/test_auth_service.py -v
```

Expected: all 6 tests pass.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/auth.py backend/tests/test_auth_service.py
git commit -m "feat: replace guessable session ID with random token in sessions table"
```

---

### Task 3: Update api/auth.py — use create_session, add logout

**Files:**
- Modify: `backend/app/api/auth.py`

`delete_record` on the `sessions` table uses `token` (text PK) not an integer id. The existing `db.delete_record(table, record_id)` passes `record_id` as the `WHERE id = %s` param — but sessions uses `token` as PK. We need to delete by token value using `db.get_records` + delete, which `delete_session` already handles.

- [ ] **Step 1: Rewrite backend/app/api/auth.py**

```python
from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import RedirectResponse
import httpx

from app.core.config import settings
from app.db.connection import db
from app.services.auth import create_session, delete_session, get_current_user
from app.services.oauth import client
from app.services.security import encrypt_token
from datetime import datetime, timedelta, timezone

router = APIRouter()

CALLBACK_URL = f'{settings.BACKEND_URL}/api/auth/callback'


@router.get('/login')
async def login(request: Request) -> RedirectResponse:
    import secrets
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

    token_data = await client.get_access_token(code, CALLBACK_URL, code_verifier=code_verifier)
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
            return Response(f'Failed to fetch MAL user info: {user_response.status_code}', status_code=502)
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
async def get_me(user: dict = Depends(get_current_user)) -> dict:
    return {'id': user['id'], 'username': user['mal_username']}
```

- [ ] **Step 2: Run the full test suite**

```bash
docker compose exec backend pytest -v
```

Expected: all tests pass.

- [ ] **Step 3: Lint**

```bash
docker compose exec backend ruff check app/api/auth.py app/services/auth.py
```

Expected: no errors.

- [ ] **Step 4: Smoke test — restart backend and verify login flow still works**

```bash
docker compose restart backend
sleep 3
docker compose logs backend --tail=10
```

Expected: `Application startup complete.` with no errors.

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/auth.py
git commit -m "feat: use token sessions in auth callback, add logout endpoint"
```

---

### Task 4: Fix delete_session to work with text PK

The existing `db.delete_record(table, record_id)` runs `DELETE FROM {table} WHERE id = %s` — but `sessions` uses `token` (text) as its primary key, not `id`. The `delete_session` function in Task 2 works around this by using `db.get_records` then `db.delete_record`, but that's roundabout and won't actually work since `delete_record` still uses `WHERE id = %s`.

The cleanest fix: add `db.delete_by` method, or simpler — just run a direct query in `delete_session` using `get_pool()`.

- [ ] **Step 1: Update delete_session in backend/app/services/auth.py**

Replace the `delete_session` function:

```python
def delete_session(token: str) -> None:
    from app.db.connection import get_pool
    from psycopg.rows import dict_row
    with get_pool().connection() as conn:
        with conn.cursor() as cur:
            cur.execute('DELETE FROM sessions WHERE token = %s', (token,))
```

- [ ] **Step 2: Update the test to match**

In `backend/tests/test_auth_service.py`, replace `test_delete_session_removes_row`:

```python
def test_delete_session_removes_row():
    pool = MagicMock()
    conn = MagicMock()
    cur = MagicMock()
    pool.connection.return_value.__enter__ = MagicMock(return_value=conn)
    pool.connection.return_value.__exit__ = MagicMock(return_value=False)
    conn.cursor.return_value.__enter__ = MagicMock(return_value=cur)
    conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

    with patch('app.services.auth.get_pool', return_value=pool):
        delete_session('tok')

    cur.execute.assert_called_once_with('DELETE FROM sessions WHERE token = %s', ('tok',))
```

- [ ] **Step 3: Run tests**

```bash
docker compose exec backend pytest tests/test_auth_service.py -v
```

Expected: all 6 pass.

- [ ] **Step 4: Commit**

```bash
git add backend/app/services/auth.py backend/tests/test_auth_service.py
git commit -m "fix: delete_session uses direct SQL for text PK, not db.delete_record"
```
