# Voice Actor Overlap Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the core IHYS feature — user searches any anime, app shows which voice actors in it also appeared in their watched anime history.

**Architecture:** Three new backend endpoints (MAL search, actors fetch with on-demand scraping, overlap query) plus a four-screen Nuxt 3 frontend. Actor data is scraped inline on first lookup and cached permanently in the `characters`/`actors`/`character_actors` tables. The overlap is computed in Python via a series of Supabase queries.

**Tech Stack:** FastAPI, Supabase Python client, BeautifulSoup (existing scrapers), httpx, Nuxt 3, Vue 3 Composition API, TypeScript, Nuxt UI

---

## File Map

**Backend — new files:**
- `backend/app/api/anime.py` — `GET /api/anime/search` and `GET /api/anime/{mal_id}/actors`
- `backend/app/services/anime_actors.py` — `ensure_actor_data()` (on-demand scrape) + `get_actor_overlap()` (core algorithm)
- `backend/tests/__init__.py`
- `backend/tests/test_overlap.py`

**Backend — modified files:**
- `backend/app/api/auth.py` — fix broken SQLAlchemy import, add `GET /me` endpoint
- `backend/app/api/user_anime.py` — add `GET /anime/{mal_id}/overlap` endpoint
- `backend/app/api/__init__.py` — export anime router
- `backend/app/main.py` — register `/api/anime` router
- `backend/app/db/connection.py` — add `get_records_by_ids()` for IN queries
- `backend/app/services/mal_api.py` — add `search_anime()` method
- `backend/pyproject.toml` — add pytest dev deps

**Frontend — new files:**
- `frontend/pages/index.vue` — login page
- `frontend/pages/dashboard.vue` — main page (search + history + overlap results)
- `frontend/composables/useAuth.ts`
- `frontend/composables/useAnimeSearch.ts`
- `frontend/composables/useAnimeOverlap.ts`

**Frontend — modified files:**
- `frontend/app.vue` — replace `NuxtWelcome` with `NuxtPage`

---

## Task 1: Fix auth.py and add /me endpoint

The current `auth.py` imports `get_session` from `connection.py` which was removed during the Supabase migration. This import error prevents the app from starting. Rewrite the callback to use the Supabase `db` and add the `/me` endpoint needed by the frontend.

**Files:**
- Modify: `backend/app/api/auth.py`

- [ ] **Step 1: Rewrite auth.py**

Replace the entire file:

```python
import secrets
from datetime import datetime, timedelta, timezone

import httpx
from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import RedirectResponse

from app.core.config import settings
from app.db.connection import db
from app.services.auth import get_current_user
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

    existing = db.get_records('users', {'mal_id': mal_id})
    if existing:
        user = db.update_record('users', existing[0]['id'], user_data)
    else:
        user = db.insert_record('users', user_data)

    response = RedirectResponse(url=f'{settings.FRONTEND_URL}/dashboard')
    response.set_cookie(
        key='session_id',
        value=f'user-{user["id"]}',
        httponly=True,
        secure=not settings.DEBUG,
        samesite='lax',
    )
    return response


@router.get('/me')
async def get_me(user: dict = Depends(get_current_user)) -> dict:
    return {'id': user['id'], 'username': user['mal_username']}
```

- [ ] **Step 2: Restart the backend and verify it starts without ImportError**

```bash
docker-compose restart backend
docker-compose logs backend --tail=20
```

Expected: no `ImportError`, logs show `Uvicorn running on http://0.0.0.0:8000`

- [ ] **Step 3: Commit**

```bash
git add backend/app/api/auth.py
git commit -m "fix: rewrite auth callback to use Supabase, add /me endpoint"
```

---

## Task 2: Add `get_records_by_ids` to DatabaseOperations

The overlap algorithm needs to filter rows by a list of IDs (SQL `IN` clause). Supabase Python client supports this via `.in_()`.

**Files:**
- Modify: `backend/app/db/connection.py`

- [ ] **Step 1: Add the method**

After the `get_records` method, add:

```python
    @staticmethod
    def get_records_by_ids(table_name: str, column: str, ids: list[int]) -> list[dict]:
        if not ids:
            return []
        result = supabase.table(table_name).select('*').in_(column, ids).execute()
        return result.data or []
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/db/connection.py
git commit -m "feat: add get_records_by_ids for IN queries"
```

---

## Task 3: Create anime_actors service

This service owns two responsibilities:
1. `ensure_actor_data` — checks if actor data exists for an anime, scrapes MAL if not
2. `get_actor_overlap` — the core algorithm: finds actors in common between a searched anime and a user's watch history

**Files:**
- Create: `backend/app/services/anime_actors.py`

- [ ] **Step 1: Write the service**

```python
import aiohttp
import logging

from app.db.connection import db
from scrapers.characters import fetch_and_insert_actors_data

logger = logging.getLogger(__name__)


async def ensure_actor_data(anime_id: int, mal_id: int) -> None:
    """Scrape and store actor/character data for an anime if not already in DB."""
    existing = db.get_records('characters', {'anime_id': anime_id})
    if existing:
        return

    characters_url = f'https://myanimelist.net/anime/{mal_id}/characters'
    logger.info(f'Scraping actors for anime_id={anime_id} mal_id={mal_id}')
    async with aiohttp.ClientSession() as session:
        await fetch_and_insert_actors_data(session, characters_url, anime_id)


def get_actor_overlap(mal_id: int, user_id: int) -> list[dict]:
    """
    Return actors who appear in the given anime AND in the user's watch history.

    Each result item:
      {
        'actor': {'id', 'name', 'photo'},
        'character_in_new_anime': {'id', 'name', 'photo'} | None,
        'appears_in': [{'id', 'name', 'mal_id'}, ...],
      }
    """
    # 1. Find the anime by MAL ID
    animes = db.get_records('anime', {'mal_id': mal_id})
    if not animes:
        return []
    anime_db_id = animes[0]['id']

    # 2. Characters in the searched anime
    chars_in_anime = db.get_records('characters', {'anime_id': anime_db_id})
    if not chars_in_anime:
        return []
    char_ids_in_anime = [c['id'] for c in chars_in_anime]

    # 3. Actors for those characters
    ca_in_anime = db.get_records_by_ids('character_actors', 'character_id', char_ids_in_anime)
    actor_ids_in_anime = {ca['actor_id'] for ca in ca_in_anime}

    # 4. User's watch history
    user_anime_records = db.get_records('user_anime', {'user_id': user_id})
    if not user_anime_records:
        return []
    user_anime_ids = [ua['anime_id'] for ua in user_anime_records]

    # 5. Characters in watched anime
    chars_in_history = db.get_records_by_ids('characters', 'anime_id', user_anime_ids)
    if not chars_in_history:
        return []
    char_ids_in_history = [c['id'] for c in chars_in_history]

    # 6. Actors in watched anime
    ca_in_history = db.get_records_by_ids('character_actors', 'character_id', char_ids_in_history)
    actor_ids_in_history = {ca['actor_id'] for ca in ca_in_history}

    # 7. Intersection
    shared_actor_ids = actor_ids_in_anime & actor_ids_in_history
    if not shared_actor_ids:
        return []

    # 8. Build lookup maps
    char_map = {c['id']: c for c in chars_in_anime}
    history_char_map = {c['id']: c for c in chars_in_history}

    actor_to_new_char: dict[int, dict | None] = {}
    for ca in ca_in_anime:
        if ca['actor_id'] in shared_actor_ids and ca['actor_id'] not in actor_to_new_char:
            actor_to_new_char[ca['actor_id']] = char_map.get(ca['character_id'])

    actor_to_history_char_ids: dict[int, list[int]] = {}
    for ca in ca_in_history:
        if ca['actor_id'] in shared_actor_ids:
            actor_to_history_char_ids.setdefault(ca['actor_id'], []).append(ca['character_id'])

    # 9. Build results
    anime_cache: dict[int, dict] = {}
    result = []

    for actor_id in shared_actor_ids:
        actor = db.get_record_by_id('actors', actor_id)
        if not actor:
            continue

        char_in_new = actor_to_new_char.get(actor_id)

        seen_anime_ids: set[int] = set()
        appears_in = []
        for char_id in actor_to_history_char_ids.get(actor_id, []):
            char = history_char_map.get(char_id)
            if not char:
                continue
            aid = char['anime_id']
            if aid in seen_anime_ids:
                continue
            seen_anime_ids.add(aid)
            if aid not in anime_cache:
                anime_cache[aid] = db.get_record_by_id('anime', aid) or {}
            a = anime_cache[aid]
            if a:
                appears_in.append({'id': a['id'], 'name': a['name'], 'mal_id': a.get('mal_id')})

        result.append({
            'actor': {'id': actor['id'], 'name': actor['name'], 'photo': actor['photo']},
            'character_in_new_anime': {
                'id': char_in_new['id'],
                'name': char_in_new['name'],
                'photo': char_in_new.get('photo'),
            } if char_in_new else None,
            'appears_in': appears_in,
        })

    return result
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/services/anime_actors.py
git commit -m "feat: add anime_actors service with ensure_actor_data and get_actor_overlap"
```

---

## Task 4: Set up pytest and write overlap tests

**Files:**
- Modify: `backend/pyproject.toml`
- Create: `backend/tests/__init__.py`
- Create: `backend/tests/test_overlap.py`

- [ ] **Step 1: Add pytest to pyproject.toml**

Add this section at the end of `backend/pyproject.toml`:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
```

- [ ] **Step 2: Install pytest in the container**

```bash
docker-compose exec backend pip install pytest
```

Expected: `Successfully installed pytest-...`

- [ ] **Step 3: Create tests/__init__.py**

Create `backend/tests/__init__.py` as an empty file.

- [ ] **Step 4: Write the failing tests**

Create `backend/tests/test_overlap.py`:

```python
from unittest.mock import MagicMock, patch

from app.services.anime_actors import get_actor_overlap


def _make_db(by_table: dict, by_ids: dict, by_id: dict) -> MagicMock:
    mock = MagicMock()

    def get_records(table: str, filters: dict | None = None) -> list:
        return by_table.get((table, tuple(sorted((filters or {}).items()))), [])

    def get_records_by_ids(table: str, column: str, ids: list) -> list:
        return by_ids.get((table, column, frozenset(ids)), [])

    def get_record_by_id(table: str, record_id: int) -> dict | None:
        return by_id.get((table, record_id))

    mock.get_records.side_effect = get_records
    mock.get_records_by_ids.side_effect = get_records_by_ids
    mock.get_record_by_id.side_effect = get_record_by_id
    return mock


def test_returns_shared_actor():
    db = _make_db(
        by_table={
            ('anime', (('mal_id', 52991),)): [{'id': 1, 'name': 'Frieren', 'mal_id': 52991}],
            ('characters', (('anime_id', 1),)): [{'id': 100, 'name': 'Frieren', 'photo': '', 'anime_id': 1}],
            ('user_anime', (('user_id', 42),)): [{'id': 1, 'user_id': 42, 'anime_id': 2}],
        },
        by_ids={
            ('character_actors', 'character_id', frozenset({100})): [{'character_id': 100, 'actor_id': 10}],
            ('characters', 'anime_id', frozenset({2})): [{'id': 200, 'name': 'Eren', 'photo': '', 'anime_id': 2}],
            ('character_actors', 'character_id', frozenset({200})): [{'character_id': 200, 'actor_id': 10}],
        },
        by_id={
            ('actors', 10): {'id': 10, 'name': 'Atsumi Tanezaki', 'photo': 'http://photo.jpg'},
            ('anime', 2): {'id': 2, 'name': 'Attack on Titan', 'mal_id': 16498},
        },
    )

    with patch('app.services.anime_actors.db', db):
        result = get_actor_overlap(52991, 42)

    assert len(result) == 1
    assert result[0]['actor']['name'] == 'Atsumi Tanezaki'
    assert result[0]['character_in_new_anime']['name'] == 'Frieren'
    assert result[0]['appears_in'][0]['name'] == 'Attack on Titan'


def test_returns_empty_when_anime_not_in_db():
    db = _make_db(
        by_table={('anime', (('mal_id', 99999),)): []},
        by_ids={},
        by_id={},
    )
    with patch('app.services.anime_actors.db', db):
        result = get_actor_overlap(99999, 42)
    assert result == []


def test_returns_empty_when_no_shared_actors():
    db = _make_db(
        by_table={
            ('anime', (('mal_id', 52991),)): [{'id': 1, 'name': 'Frieren', 'mal_id': 52991}],
            ('characters', (('anime_id', 1),)): [{'id': 100, 'name': 'Frieren', 'photo': '', 'anime_id': 1}],
            ('user_anime', (('user_id', 42),)): [{'id': 1, 'user_id': 42, 'anime_id': 2}],
        },
        by_ids={
            ('character_actors', 'character_id', frozenset({100})): [{'character_id': 100, 'actor_id': 10}],
            ('characters', 'anime_id', frozenset({2})): [{'id': 200, 'name': 'Eren', 'photo': '', 'anime_id': 2}],
            ('character_actors', 'character_id', frozenset({200})): [{'character_id': 200, 'actor_id': 99}],
        },
        by_id={},
    )
    with patch('app.services.anime_actors.db', db):
        result = get_actor_overlap(52991, 42)
    assert result == []


def test_returns_empty_when_user_has_no_history():
    db = _make_db(
        by_table={
            ('anime', (('mal_id', 52991),)): [{'id': 1, 'name': 'Frieren', 'mal_id': 52991}],
            ('characters', (('anime_id', 1),)): [{'id': 100, 'name': 'Frieren', 'photo': '', 'anime_id': 1}],
            ('user_anime', (('user_id', 42),)): [],
        },
        by_ids={
            ('character_actors', 'character_id', frozenset({100})): [{'character_id': 100, 'actor_id': 10}],
        },
        by_id={},
    )
    with patch('app.services.anime_actors.db', db):
        result = get_actor_overlap(52991, 42)
    assert result == []
```

- [ ] **Step 5: Run tests and verify they pass**

```bash
docker-compose exec backend pytest tests/test_overlap.py -v
```

Expected output:
```
tests/test_overlap.py::test_returns_shared_actor PASSED
tests/test_overlap.py::test_returns_empty_when_anime_not_in_db PASSED
tests/test_overlap.py::test_returns_empty_when_no_shared_actors PASSED
tests/test_overlap.py::test_returns_empty_when_user_has_no_history PASSED
4 passed
```

- [ ] **Step 6: Commit**

```bash
git add backend/pyproject.toml backend/tests/
git commit -m "test: add pytest setup and overlap algorithm unit tests"
```

---

## Task 5: Add anime search to MALApiService

**Files:**
- Modify: `backend/app/services/mal_api.py`

- [ ] **Step 1: Add the import and method**

At the top of `mal_api.py`, `settings` is not yet imported. Add it to the existing imports:

```python
from app.core.config import settings
```

Then add this method to the `MALApiService` class (after `sync_user_anime_list`):

```python
    async def search_anime(self, query: str, limit: int = 10) -> list[dict]:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f'{self.BASE_URL}/anime',
                headers={'X-MAL-CLIENT-ID': settings.MAL_CLIENT_ID},
                params={
                    'q': query,
                    'limit': limit,
                    'fields': 'id,title,main_picture,start_date',
                },
            )
            if response.status_code != 200:
                raise MALApiError(f'MAL search failed: {response.status_code}')

            data = response.json()
            return [
                {
                    'mal_id': item['node']['id'],
                    'title': item['node']['title'],
                    'image': item['node'].get('main_picture', {}).get('medium'),
                    'year': item['node'].get('start_date', '')[:4]
                    if item['node'].get('start_date')
                    else None,
                }
                for item in data.get('data', [])
            ]
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/services/mal_api.py
git commit -m "feat: add search_anime to MALApiService"
```

---

## Task 6: Create anime API router

**Files:**
- Create: `backend/app/api/anime.py`

- [ ] **Step 1: Write the router**

```python
from typing import Any

from fastapi import APIRouter, HTTPException, status

from app.db.connection import db
from app.services.anime_actors import ensure_actor_data
from app.services.mal_api import MALApiError, MALApiService

router = APIRouter()


@router.get('/search')
async def search_anime(q: str = '') -> list[dict[str, Any]]:
    if len(q) < 2:
        return []
    mal_service = MALApiService()
    try:
        return await mal_service.search_anime(q)
    except MALApiError as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))


@router.get('/{mal_id}/actors')
async def get_anime_actors(mal_id: int) -> dict[str, Any]:
    animes = db.get_records('anime', {'mal_id': mal_id})
    if not animes:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'Anime with MAL ID {mal_id} not found in database',
        )
    anime = animes[0]

    try:
        await ensure_actor_data(anime['id'], mal_id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f'Could not fetch actor data: {str(e)}',
        )

    char_ids = [c['id'] for c in db.get_records('characters', {'anime_id': anime['id']})]
    char_actors = db.get_records_by_ids('character_actors', 'character_id', char_ids)
    actor_ids = list({ca['actor_id'] for ca in char_actors})
    actors = db.get_records_by_ids('actors', 'id', actor_ids)

    return {'anime': anime, 'actors': actors}
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/api/anime.py
git commit -m "feat: add anime search and actors API endpoints"
```

---

## Task 7: Add overlap endpoint to user_anime router

**Files:**
- Modify: `backend/app/api/user_anime.py`

- [ ] **Step 1: Add imports at the top of user_anime.py**

After the existing imports, add:

```python
from app.services.anime_actors import ensure_actor_data, get_actor_overlap
```

- [ ] **Step 2: Add the endpoint**

Add this route at the end of the file:

```python
@router.get('/anime/{mal_id}/overlap')
async def get_anime_overlap(
    mal_id: int,
    request: Request,
    user_id: int = Depends(get_current_user_id),
) -> list[dict[str, Any]]:
    animes = db.get_records('anime', {'mal_id': mal_id})
    if not animes:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'Anime with MAL ID {mal_id} not found in database',
        )
    anime = animes[0]

    try:
        await ensure_actor_data(anime['id'], mal_id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f'Could not fetch actor data: {str(e)}',
        )

    return get_actor_overlap(mal_id, user_id)
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/api/user_anime.py
git commit -m "feat: add GET /api/user/anime/{mal_id}/overlap endpoint"
```

---

## Task 8: Register the anime router

**Files:**
- Modify: `backend/app/api/__init__.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: Export anime from __init__.py**

Replace the contents of `backend/app/api/__init__.py`:

```python
from . import anime, auth, user_anime

__all__ = ['anime', 'auth', 'user_anime']
```

- [ ] **Step 2: Register router in main.py**

In `backend/app/main.py`, add the import and router registration:

```python
from app.api import auth, user_anime, anime
```

And after the existing `app.include_router` calls:

```python
app.include_router(anime.router, prefix='/api/anime', tags=['Anime'])
```

- [ ] **Step 3: Restart backend and smoke-test**

```bash
docker-compose restart backend
```

```bash
curl http://localhost:8002/api/anime/search?q=frieren
```

Expected: JSON array of anime results from MAL.

- [ ] **Step 4: Commit**

```bash
git add backend/app/api/__init__.py backend/app/main.py
git commit -m "feat: register anime router at /api/anime"
```

---

## Task 9: Frontend setup — app.vue, login page, auth composable

**Files:**
- Modify: `frontend/app.vue`
- Create: `frontend/composables/useAuth.ts`
- Create: `frontend/pages/index.vue`

- [ ] **Step 1: Update app.vue**

Replace the contents of `frontend/app.vue`:

```vue
<template>
  <NuxtRouteAnnouncer />
  <NuxtPage />
</template>
```

- [ ] **Step 2: Create useAuth composable**

Create `frontend/composables/useAuth.ts`:

```typescript
export interface AuthUser {
  id: number
  username: string
}

export const useAuth = () => {
  const config = useRuntimeConfig()
  const user = useState<AuthUser | null>('auth-user', () => null)

  const checkAuth = async (): Promise<boolean> => {
    try {
      const data = await $fetch<AuthUser>('/api/auth/me', {
        baseURL: config.public.apiBase,
        credentials: 'include',
      })
      user.value = data
      return true
    } catch {
      user.value = null
      return false
    }
  }

  return { user, checkAuth }
}
```

- [ ] **Step 3: Create the login page**

Create `frontend/pages/index.vue`:

```vue
<script setup lang="ts">
const { checkAuth } = useAuth()
const config = useRuntimeConfig()

const checking = ref(true)

onMounted(async () => {
  const authenticated = await checkAuth()
  if (authenticated) {
    await navigateTo('/dashboard')
  }
  checking.value = false
})

const loginUrl = `${config.public.apiBase}/api/auth/login`
</script>

<template>
  <div class="flex min-h-screen items-center justify-center bg-gray-950">
    <div v-if="!checking" class="text-center">
      <h1 class="text-4xl font-bold mb-2">IHYS</h1>
      <p class="text-gray-400 mb-8">In how many animes you've seen this actor?</p>
      <UButton :to="loginUrl" external size="lg" color="primary">
        Login with MyAnimeList
      </UButton>
    </div>
  </div>
</template>
```

- [ ] **Step 4: Start frontend dev server and verify login page loads**

```bash
cd frontend && npm run dev
```

Open http://localhost:3000 — should show the IHYS login page with the MAL button.

- [ ] **Step 5: Commit**

```bash
git add frontend/app.vue frontend/composables/useAuth.ts frontend/pages/index.vue
git commit -m "feat: add login page and useAuth composable"
```

---

## Task 10: Dashboard — auth guard, watch history, MAL sync

**Files:**
- Create: `frontend/pages/dashboard.vue`

- [ ] **Step 1: Create the dashboard page**

Create `frontend/pages/dashboard.vue`:

```vue
<script setup lang="ts">
const { user, checkAuth } = useAuth()
const config = useRuntimeConfig()

const watchHistory = ref<Array<{
  id: number
  anime: { id: number; name: string; mal_id: number | null }
  watch_status: string
}>>([])
const loadingHistory = ref(true)
const syncing = ref(false)

onMounted(async () => {
  const authenticated = await checkAuth()
  if (!authenticated) {
    await navigateTo('/')
    return
  }
  await loadWatchHistory()
})

async function loadWatchHistory() {
  loadingHistory.value = true
  try {
    watchHistory.value = await $fetch('/api/user/anime', {
      baseURL: config.public.apiBase,
      credentials: 'include',
    })
  } catch {
    watchHistory.value = []
  } finally {
    loadingHistory.value = false
  }
}

async function syncFromMal() {
  syncing.value = true
  try {
    await $fetch('/api/user/anime/sync', {
      method: 'POST',
      baseURL: config.public.apiBase,
      credentials: 'include',
    })
    await loadWatchHistory()
  } finally {
    syncing.value = false
  }
}
</script>

<template>
  <div class="max-w-2xl mx-auto p-4">
    <!-- Header -->
    <div class="flex items-center justify-between mb-6">
      <h1 class="text-2xl font-bold">IHYS</h1>
      <div class="flex items-center gap-3">
        <span class="text-gray-400 text-sm">{{ user?.username }}</span>
        <UButton size="sm" variant="outline" :loading="syncing" @click="syncFromMal">
          Sync from MAL
        </UButton>
      </div>
    </div>

    <!-- Search placeholder (Task 11) -->

    <!-- Watch history -->
    <div class="mt-6">
      <p class="text-xs text-gray-500 uppercase tracking-widest mb-3">
        Watch history ({{ watchHistory.length }})
      </p>
      <div v-if="loadingHistory" class="text-gray-400 text-sm">Loading...</div>
      <div v-else class="flex flex-col gap-1">
        <div
          v-for="entry in watchHistory"
          :key="entry.id"
          class="flex items-center justify-between bg-gray-900 rounded px-3 py-2 text-sm"
        >
          <span>{{ entry.anime.name }}</span>
          <span class="text-gray-500 capitalize">{{ entry.watch_status }}</span>
        </div>
        <div v-if="watchHistory.length === 0" class="text-gray-500 text-sm">
          No anime yet — sync from MAL to get started.
        </div>
      </div>
    </div>
  </div>
</template>
```

- [ ] **Step 2: Log in via MAL and verify the dashboard loads with watch history**

Click the MAL button on the login page. After the OAuth redirect, you should land on `/dashboard` and see the watch history list. If the list is empty, click "Sync from MAL".

- [ ] **Step 3: Commit**

```bash
git add frontend/pages/dashboard.vue
git commit -m "feat: add dashboard with watch history and MAL sync"
```

---

## Task 11: Anime search autocomplete

**Files:**
- Create: `frontend/composables/useAnimeSearch.ts`
- Modify: `frontend/pages/dashboard.vue`

- [ ] **Step 1: Create useAnimeSearch composable**

Create `frontend/composables/useAnimeSearch.ts`:

```typescript
export interface AnimeSearchResult {
  mal_id: number
  title: string
  image: string | null
  year: string | null
}

export const useAnimeSearch = () => {
  const config = useRuntimeConfig()
  const results = ref<AnimeSearchResult[]>([])
  const loading = ref(false)
  let timer: ReturnType<typeof setTimeout> | null = null

  const search = (query: string) => {
    if (timer) clearTimeout(timer)
    if (!query || query.length < 2) {
      results.value = []
      return
    }
    timer = setTimeout(async () => {
      loading.value = true
      try {
        results.value = await $fetch<AnimeSearchResult[]>('/api/anime/search', {
          baseURL: config.public.apiBase,
          credentials: 'include',
          params: { q: query },
        })
      } catch {
        results.value = []
      } finally {
        loading.value = false
      }
    }, 300)
  }

  const clear = () => {
    if (timer) clearTimeout(timer)
    results.value = []
  }

  return { results, loading, search, clear }
}
```

- [ ] **Step 2: Add search UI to dashboard.vue**

In the `<script setup>` section of `frontend/pages/dashboard.vue`, add after the `syncing` ref:

```typescript
const { results: searchResults, loading: searching, search, clear: clearSearch } = useAnimeSearch()
const searchQuery = ref('')
const showDropdown = computed(() => searchResults.value.length > 0)

function onSearchInput() {
  search(searchQuery.value)
}
```

Replace the `<!-- Search placeholder (Task 11) -->` comment in the template with:

```vue
    <!-- Anime search -->
    <div class="relative">
      <UInput
        v-model="searchQuery"
        placeholder="Search any anime..."
        icon="i-heroicons-magnifying-glass"
        :loading="searching"
        @input="onSearchInput"
      />
      <div
        v-if="showDropdown"
        class="absolute z-10 w-full bg-gray-900 border border-gray-700 rounded-md shadow-lg mt-1 overflow-hidden"
      >
        <button
          v-for="anime in searchResults"
          :key="anime.mal_id"
          class="w-full text-left px-4 py-2 hover:bg-gray-800 flex items-center justify-between text-sm"
          @click="selectAnime(anime)"
        >
          <span>{{ anime.title }}</span>
          <span class="text-gray-500">{{ anime.year }}</span>
        </button>
      </div>
    </div>
```

- [ ] **Step 3: Type a few characters in the search box and verify the dropdown appears**

Open http://localhost:3000/dashboard, type "frieren" — a dropdown with matching anime should appear within 300ms.

- [ ] **Step 4: Commit**

```bash
git add frontend/composables/useAnimeSearch.ts frontend/pages/dashboard.vue
git commit -m "feat: add anime search autocomplete to dashboard"
```

---

## Task 12: Overlap results display

**Files:**
- Create: `frontend/composables/useAnimeOverlap.ts`
- Modify: `frontend/pages/dashboard.vue`

- [ ] **Step 1: Create useAnimeOverlap composable**

Create `frontend/composables/useAnimeOverlap.ts`:

```typescript
export interface OverlapResult {
  actor: { id: number; name: string; photo: string }
  character_in_new_anime: { id: number; name: string; photo: string | null } | null
  appears_in: Array<{ id: number; name: string; mal_id: number | null }>
}

export const useAnimeOverlap = () => {
  const config = useRuntimeConfig()
  const overlap = ref<OverlapResult[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  const fetchOverlap = async (malId: number) => {
    loading.value = true
    error.value = null
    try {
      overlap.value = await $fetch<OverlapResult[]>(`/api/user/anime/${malId}/overlap`, {
        baseURL: config.public.apiBase,
        credentials: 'include',
      })
    } catch (e: unknown) {
      const err = e as { data?: { detail?: string } }
      error.value = err?.data?.detail ?? 'Could not fetch actor data, try again'
      overlap.value = []
    } finally {
      loading.value = false
    }
  }

  return { overlap, loading, error, fetchOverlap }
}
```

- [ ] **Step 2: Wire up overlap to the dashboard**

In `<script setup>` of `frontend/pages/dashboard.vue`, add:

```typescript
const { overlap, loading: loadingOverlap, error: overlapError, fetchOverlap } = useAnimeOverlap()
const selectedAnime = ref<{ mal_id: number; title: string } | null>(null)

async function selectAnime(anime: { mal_id: number; title: string; image: string | null; year: string | null }) {
  selectedAnime.value = anime
  searchQuery.value = anime.title
  clearSearch()
  await fetchOverlap(anime.mal_id)
}
```

Add this section at the end of the template (after the watch history block):

```vue
    <!-- Overlap results -->
    <div v-if="selectedAnime" class="mt-8">
      <h2 class="text-lg font-semibold mb-1">{{ selectedAnime.title }}</h2>

      <div v-if="loadingOverlap" class="text-gray-400 text-sm">
        Fetching actor data... (first lookup may take a few seconds)
      </div>
      <div v-else-if="overlapError" class="text-red-400 text-sm">{{ overlapError }}</div>
      <div v-else-if="overlap.length === 0" class="text-gray-500 text-sm">
        No shared voice actors found.
      </div>
      <div v-else>
        <p class="text-xs text-gray-500 uppercase tracking-widest mb-3">
          {{ overlap.length }} shared voice actor{{ overlap.length !== 1 ? 's' : '' }}
        </p>
        <div class="flex flex-col gap-3">
          <div
            v-for="item in overlap"
            :key="item.actor.id"
            class="bg-gray-900 rounded-lg p-3 flex items-start gap-3"
          >
            <img
              v-if="item.actor.photo"
              :src="item.actor.photo"
              :alt="item.actor.name"
              class="w-10 h-10 rounded-full object-cover flex-shrink-0"
            />
            <div class="flex-1">
              <p class="font-medium">{{ item.actor.name }}</p>
              <p v-if="item.character_in_new_anime" class="text-sm text-gray-400 mb-2">
                as {{ item.character_in_new_anime.name }}
              </p>
              <div class="flex flex-wrap gap-2">
                <span
                  v-for="a in item.appears_in"
                  :key="a.id"
                  class="bg-gray-800 text-blue-300 text-xs px-2 py-1 rounded-full"
                >
                  {{ a.name }}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
```

- [ ] **Step 3: End-to-end test**

1. Open http://localhost:3000/dashboard
2. Sync from MAL if not done yet
3. Type an anime title in the search box (e.g. "Attack on Titan")
4. Click a result from the dropdown
5. Wait for results — first lookup will scrape MAL (a few seconds), subsequent ones are instant
6. Verify actor cards appear with character names and anime tags

- [ ] **Step 4: Run the backend tests one final time**

```bash
docker-compose exec backend pytest tests/ -v
```

Expected: all 4 tests pass.

- [ ] **Step 5: Commit**

```bash
git add frontend/composables/useAnimeOverlap.ts frontend/pages/dashboard.vue
git commit -m "feat: add voice actor overlap results to dashboard"
```
