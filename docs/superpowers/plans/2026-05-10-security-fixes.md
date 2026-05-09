# Security Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the four production-blocking security issues: hardcoded CORS origin, unauthenticated scraping endpoints, SSRF via `anime_url`, and raw exception messages leaking to clients.

**Architecture:** Four independent fixes across `main.py`, `api/anime.py`, `api/user_anime.py`, and `serializers.py`. No new tables or dependencies required. Each fix is isolated to one or two files.

**Tech Stack:** FastAPI, Pydantic v2, existing auth dependency (`get_current_user_id`).

---

### Task 1: Fix CORS to use FRONTEND_URL from config

**Files:**
- Modify: `backend/app/main.py`

The `origins` list is hardcoded to `['http://localhost:3000']`. It should read from `settings.FRONTEND_URL` so production deployments work without code changes.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_cors.py`:

```python
from unittest.mock import patch

from fastapi.testclient import TestClient


def test_cors_allows_configured_frontend_url():
    with patch.dict('os.environ', {'FRONTEND_URL': 'https://ihys.example.com'}):
        # Re-import app with patched settings
        import importlib
        import app.core.config as config_module
        import app.main as main_module

        importlib.reload(config_module)
        importlib.reload(main_module)

        client = TestClient(main_module.app)
        response = client.get(
            '/',
            headers={'Origin': 'https://ihys.example.com'},
        )
        assert 'access-control-allow-origin' in response.headers
        assert response.headers['access-control-allow-origin'] == 'https://ihys.example.com'
```

- [ ] **Step 2: Run test to verify it fails**

```bash
docker compose exec backend pytest tests/test_cors.py -v 2>&1 | tail -15
```

Expected: FAIL — CORS header will be `http://localhost:3000` not the configured URL.

- [ ] **Step 3: Update main.py**

Replace:

```python
origins = [
    'http://localhost:3000',
]
```

With:

```python
origins = [settings.FRONTEND_URL]
```

Full updated `backend/app/main.py`:

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from app.api import anime, auth, user_anime
from app.core.config import settings

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

app.add_middleware(SessionMiddleware, secret_key=settings.ENCRYPTION_KEY.decode())

app.include_router(auth.router, prefix='/api/auth', tags=['Authentication'])
app.include_router(user_anime.router, prefix='/api/user', tags=['User Anime'])
app.include_router(anime.router, prefix='/api/anime', tags=['Anime'])


@app.get('/')
def read_root() -> dict:
    return {'status': 'Backend is running!'}
```

- [ ] **Step 4: Run test to verify it passes**

```bash
docker compose exec backend pytest tests/test_cors.py -v 2>&1 | tail -10
```

Expected: PASS.

- [ ] **Step 5: Run full test suite**

```bash
docker compose exec backend pytest -v 2>&1 | tail -10
```

Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add backend/app/main.py backend/tests/test_cors.py
git commit -m "fix: CORS origin reads from FRONTEND_URL setting, not hardcoded localhost"
```

---

### Task 2: Require authentication on anime scraping endpoints

**Files:**
- Modify: `backend/app/api/anime.py`

`GET /api/anime/search` and `GET /api/anime/{mal_id}/actors` are currently unauthenticated. Any anonymous user can trigger MAL API calls and actor scraping. Both endpoints should require a valid session.

- [ ] **Step 1: Write failing tests**

Create `backend/tests/test_anime_auth.py`:

```python
from unittest.mock import patch, AsyncMock, MagicMock

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app, raise_server_exceptions=False)


def test_search_requires_auth():
    response = client.get('/api/anime/search?q=naruto')
    assert response.status_code == 401


def test_get_actors_requires_auth():
    response = client.get('/api/anime/123/actors')
    assert response.status_code == 401


def test_search_works_when_authenticated():
    mock_user = {'id': 1, 'mal_username': 'testuser'}
    with patch('app.services.auth.get_current_user', return_value=mock_user):
        with patch('app.services.mal_api.MALApiService.search_anime', new_callable=AsyncMock, return_value=[]):
            response = client.get(
                '/api/anime/search?q=naruto',
                cookies={'session_id': 'fake-token'},
            )
    assert response.status_code == 200
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
docker compose exec backend pytest tests/test_anime_auth.py -v 2>&1 | tail -15
```

Expected: `test_search_requires_auth` and `test_get_actors_requires_auth` FAIL (currently return 200, not 401).

- [ ] **Step 3: Add auth dependency to anime.py**

```python
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request, status

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
    except MALApiError as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail='Search failed')


@router.get('/{mal_id}/actors')
async def get_anime_actors(
    mal_id: int,
    user_id: Annotated[int, Depends(get_current_user_id)] = 0,
) -> dict[str, Any]:
    try:
        anime = await ensure_anime_exists(mal_id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail='Could not fetch anime info',
        )
    if not anime:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'Anime with MAL ID {mal_id} not found',
        )

    try:
        await ensure_actor_data(anime['id'], mal_id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail='Could not fetch actor data',
        )

    char_ids = [c['id'] for c in db.get_records('characters', {'anime_id': anime['id']})]
    char_actors = db.get_records_by_ids('character_actors', 'character_id', char_ids)
    actor_ids = list({ca['actor_id'] for ca in char_actors})
    actors = db.get_records_by_ids('actors', 'id', actor_ids)

    return {'anime': anime, 'actors': actors}
```

Note: error messages no longer leak `str(e)` — fixed as part of this task (see Task 4 goals).

- [ ] **Step 4: Run tests to verify they pass**

```bash
docker compose exec backend pytest tests/test_anime_auth.py -v 2>&1 | tail -15
```

Expected: all 3 pass.

- [ ] **Step 5: Run ruff**

```bash
docker compose exec backend ruff check app/api/anime.py
```

Expected: no errors.

- [ ] **Step 6: Commit**

```bash
git add backend/app/api/anime.py backend/tests/test_anime_auth.py
git commit -m "fix: require authentication on anime search and actors endpoints"
```

---

### Task 3: Validate anime_url against MAL hostname (SSRF fix)

**Files:**
- Modify: `backend/app/serializers.py`

`AddAnimeRequest.anime_url` is `Optional[str]` with no validation. An authenticated user can supply any URL (e.g. `http://169.254.169.254/`) and the server will make an HTTP request to it. Constrain it to MAL URLs only.

- [ ] **Step 1: Write failing tests**

Create `backend/tests/test_serializers.py`:

```python
import pytest
from pydantic import ValidationError

from app.serializers import AddAnimeRequest


def test_valid_mal_url_accepted():
    req = AddAnimeRequest(
        anime_name='Naruto',
        anime_url='https://myanimelist.net/anime/20/Naruto',
    )
    assert req.anime_url == 'https://myanimelist.net/anime/20/Naruto'


def test_none_url_accepted():
    req = AddAnimeRequest(anime_name='Naruto', anime_url=None)
    assert req.anime_url is None


def test_non_mal_url_rejected():
    with pytest.raises(ValidationError):
        AddAnimeRequest(
            anime_name='Naruto',
            anime_url='http://169.254.169.254/latest/meta-data/',
        )


def test_internal_url_rejected():
    with pytest.raises(ValidationError):
        AddAnimeRequest(
            anime_name='Naruto',
            anime_url='http://localhost:8080/internal',
        )


def test_other_domain_rejected():
    with pytest.raises(ValidationError):
        AddAnimeRequest(
            anime_name='Naruto',
            anime_url='https://evil.com/fake',
        )
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
docker compose exec backend pytest tests/test_serializers.py -v 2>&1 | tail -15
```

Expected: `test_non_mal_url_rejected`, `test_internal_url_rejected`, `test_other_domain_rejected` FAIL (currently no validation).

- [ ] **Step 3: Add URL validator to serializers.py**

```python
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, field_validator


class AnimeResponse(BaseModel):
    id: int
    name: str
    english_title: Optional[str] = None
    japanese_title: Optional[str] = None
    episodes: Optional[str] = None
    status: Optional[str] = None
    aired: Optional[str] = None
    score: Optional[str] = None
    synopsis: Optional[str] = None
    mal_id: Optional[int] = None


class UserAnimeResponse(BaseModel):
    id: int
    anime: AnimeResponse
    watch_status: str
    score: Optional[int] = None
    episodes_watched: Optional[int] = None
    start_date: Optional[str] = None
    finish_date: Optional[str] = None
    is_synced_from_mal: bool


class AddAnimeRequest(BaseModel):
    anime_name: str
    anime_url: Optional[str] = None
    watch_status: str = 'completed'
    score: Optional[int] = None
    episodes_watched: Optional[int] = None
    start_date: Optional[str] = None
    finish_date: Optional[str] = None

    @field_validator('anime_url')
    @classmethod
    def anime_url_must_be_mal(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        from urllib.parse import urlparse
        parsed = urlparse(v)
        if parsed.hostname != 'myanimelist.net':
            raise ValueError('anime_url must be a myanimelist.net URL')
        return v


class UpdateAnimeRequest(BaseModel):
    watch_status: Optional[str] = None
    score: Optional[int] = None
    episodes_watched: Optional[int] = None
    start_date: Optional[str] = None
    finish_date: Optional[str] = None


class UserResponse(BaseModel):
    id: int
    mal_id: str
    mal_username: str
    auth_user_id: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class ActorResponse(BaseModel):
    id: int
    name: str
    photo: str
    created_at: Optional[datetime] = None


class CharacterResponse(BaseModel):
    id: int
    name: str
    photo: str
    anime_id: int
    created_at: Optional[datetime] = None


class CharacterActorResponse(BaseModel):
    id: int
    character_id: int
    actor_id: int
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
docker compose exec backend pytest tests/test_serializers.py -v 2>&1 | tail -10
```

Expected: all 5 pass.

- [ ] **Step 5: Run ruff**

```bash
docker compose exec backend ruff check app/serializers.py
```

Expected: no errors.

- [ ] **Step 6: Commit**

```bash
git add backend/app/serializers.py backend/tests/test_serializers.py
git commit -m "fix: validate anime_url must be myanimelist.net to prevent SSRF"
```

---

### Task 4: Stop leaking raw exception messages to clients

**Files:**
- Modify: `backend/app/api/user_anime.py`

Three places in `user_anime.py` return raw `str(e)` or `e!s` in HTTP error responses, which can expose internal paths, DB errors, or stack traces to clients.

Lines to fix:
- Line 51: `detail=f'Failed to fetch anime list: {e!s}'`
- Line 74: `detail=f'Sync failed: {e!s}'`
- Line 170: `detail=f'Failed to add anime: {e!s}'`

`anime.py` errors were already cleaned up in Task 2.

- [ ] **Step 1: Write failing tests**

Create `backend/tests/test_error_messages.py`:

```python
from unittest.mock import patch, MagicMock

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app, raise_server_exceptions=False)

MOCK_USER = {'id': 1, 'mal_username': 'testuser'}


def authed_get(path):
    with patch('app.services.auth.get_current_user', return_value=MOCK_USER):
        return client.get(path, cookies={'session_id': 'tok'})


def authed_post(path, json=None):
    with patch('app.services.auth.get_current_user', return_value=MOCK_USER):
        return client.post(path, json=json or {}, cookies={'session_id': 'tok'})


def test_anime_list_error_does_not_leak_exception():
    with patch('app.api.user_anime.db') as mock_db:
        mock_db.get_records.side_effect = Exception('secret internal db error xyz')
        response = authed_get('/api/user/anime')
    assert response.status_code == 500
    assert 'secret internal db error xyz' not in response.text


def test_sync_error_does_not_leak_exception():
    with patch('app.api.user_anime.MALApiService') as mock_svc:
        instance = MagicMock()
        instance.sync_user_anime_list.side_effect = Exception('secret internal sync error xyz')
        mock_svc.return_value = instance
        response = authed_post('/api/user/anime/sync')
    assert response.status_code == 500
    assert 'secret internal sync error xyz' not in response.text
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
docker compose exec backend pytest tests/test_error_messages.py -v 2>&1 | tail -15
```

Expected: both tests FAIL — exception text currently leaks into response body.

- [ ] **Step 3: Fix the three error handlers in user_anime.py**

Replace line 51:
```python
            detail=f'Failed to fetch anime list: {e!s}',
```
With:
```python
            detail='Failed to fetch anime list',
```

Replace line 74:
```python
            detail=f'Sync failed: {e!s}',
```
With:
```python
            detail='Sync failed',
```

Replace line 170:
```python
            detail=f'Failed to add anime: {e!s}',
```
With:
```python
            detail='Failed to add anime',
```

Also add logging so errors aren't silently swallowed. At the top of `user_anime.py`, after the existing imports, add:

```python
import logging
logger = logging.getLogger(__name__)
```

And in each of the three except blocks, add a `logger.exception(...)` call before the `raise HTTPException`:

Line ~49 block:
```python
    except Exception as e:
        logger.exception('Failed to fetch anime list for user %s', user_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='Failed to fetch anime list',
        )
```

Line ~71 block:
```python
    except Exception as e:
        logger.exception('Sync failed for user %s', user_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='Sync failed',
        )
```

Line ~167 block:
```python
    except HTTPException:
        raise
    except Exception as e:
        logger.exception('Failed to add anime for user %s', user_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='Failed to add anime',
        )
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
docker compose exec backend pytest tests/test_error_messages.py -v 2>&1 | tail -10
```

Expected: both pass.

- [ ] **Step 5: Run full test suite**

```bash
docker compose exec backend pytest -v 2>&1 | tail -15
```

Expected: all pass.

- [ ] **Step 6: Run ruff**

```bash
docker compose exec backend ruff check app/api/user_anime.py
```

Expected: no errors.

- [ ] **Step 7: Commit**

```bash
git add backend/app/api/user_anime.py backend/tests/test_error_messages.py
git commit -m "fix: stop leaking raw exception messages in HTTP error responses"
```
