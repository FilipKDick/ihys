# Migrate from Supabase to self-hosted Postgres Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the Supabase PostgREST client with direct psycopg3 connections to a Postgres container, eliminating ~80ms network round-trips per query.

**Architecture:** Add a `postgres` service to `compose.yml`. Rewrite `app/db/connection.py` so `DatabaseOperations` talks to Postgres directly via psycopg3. Update `config.py` to read `DATABASE_URL`. Keep the same `db.*` method signatures so no other files need changes. Apply the existing migration SQL at container startup.

**Tech Stack:** psycopg[binary] (psycopg3), Docker Postgres 17, python-dotenv, existing FastAPI/Pydantic-settings stack.

---

### Task 1: Add Postgres service to compose.yml and swap backend env

**Files:**
- Modify: `compose.yml`
- Modify: `.env.backend` (env var additions)

- [ ] **Step 1: Add postgres service and wire backend to it**

Replace the contents of `compose.yml` with:

```yaml
services:
  postgres:
    image: postgres:17
    container_name: ihys_postgres
    restart: unless-stopped
    environment:
      POSTGRES_DB: ihys
      POSTGRES_USER: ihys
      POSTGRES_PASSWORD: ihys
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./supabase/migrations:/docker-entrypoint-initdb.d
    ports:
      - "5432:5432"

  backend:
    container_name: ihys_backend
    build:
      context: ./backend
      target: ${DOCKER_TARGET:-dev}
    restart: unless-stopped
    ports:
      - "8002:8000"
    volumes:
      - ./backend:/app
    env_file:
      - ./.env.backend
    depends_on:
      postgres:
        condition: service_healthy

  frontend:
    container_name: ihys_frontend
    build:
      context: ./frontend
      target: ${DOCKER_TARGET:-dev}
    restart: unless-stopped
    ports:
      - "3000:3000"
    volumes:
      - ./frontend:/app
      - /app/node_modules
      - /app/.nuxt
    env_file:
      - ./.env.frontend
    environment:
      - NUXT_HOST=0.0.0.0
    depends_on:
      - backend

volumes:
  postgres_data:
```

- [ ] **Step 2: Add healthcheck to postgres service**

The `depends_on: condition: service_healthy` above requires a healthcheck. Add it to the postgres service block:

```yaml
  postgres:
    image: postgres:17
    container_name: ihys_postgres
    restart: unless-stopped
    environment:
      POSTGRES_DB: ihys
      POSTGRES_USER: ihys
      POSTGRES_PASSWORD: ihys
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./supabase/migrations:/docker-entrypoint-initdb.d
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ihys -d ihys"]
      interval: 5s
      timeout: 5s
      retries: 10
```

- [ ] **Step 3: Add DATABASE_URL to .env.backend**

Append to `.env.backend`:

```
DATABASE_URL=postgresql://ihys:ihys@postgres:5432/ihys
```

Keep the existing Supabase vars in place for now — they'll be removed in a later task once everything works.

- [ ] **Step 4: Commit**

```bash
git add compose.yml .env.backend
git commit -m "infra: add postgres container, wire backend dependency"
```

---

### Task 2: Fix migration SQL for plain Postgres (remove Supabase-isms)

**Files:**
- Modify: `supabase/migrations/20260509171000_create_app_schema.sql`

The existing migration ends with `notify pgrst, 'reload schema';` which is a PostgREST-specific command and will error on plain Postgres. Also the `public.` schema prefix is fine but the `notify` line must go.

- [ ] **Step 1: Remove the notify line**

Edit `supabase/migrations/20260509171000_create_app_schema.sql` — delete the last line:

```sql
notify pgrst, 'reload schema';
```

The file should end after the last `create index` statement.

- [ ] **Step 2: Verify the SQL is valid**

```bash
docker-compose up postgres -d
sleep 5
docker-compose exec postgres psql -U ihys -d ihys -c "\dt public.*"
```

Expected output: table list including `users`, `anime`, `actors`, `characters`, `character_actors`, `user_anime`.

- [ ] **Step 3: Commit**

```bash
git add supabase/migrations/20260509171000_create_app_schema.sql
git commit -m "fix: remove pgrst notify from migration, plain postgres compat"
```

---

### Task 3: Add psycopg3 to backend dependencies

**Files:**
- Modify: `backend/pyproject.toml`

- [ ] **Step 1: Add psycopg[binary] to dependencies**

In `backend/pyproject.toml`, add to the `dependencies` list:

```toml
"psycopg[binary]>=3.2.0",
```

Remove `psycopg2-binary` from `requirements.txt` (it's a different major version). Also remove `supabase` and `postgrest` from `pyproject.toml` dependencies — they will no longer be used.

- [ ] **Step 2: Rebuild the backend image**

```bash
docker-compose build backend
```

Expected: build succeeds, `psycopg` is installed.

- [ ] **Step 3: Verify psycopg imports**

```bash
docker-compose run --rm backend python -c "import psycopg; print(psycopg.__version__)"
```

Expected: prints version like `3.2.x`.

- [ ] **Step 4: Commit**

```bash
git add backend/pyproject.toml backend/requirements.txt
git commit -m "deps: swap supabase/postgrest for psycopg3"
```

---

### Task 4: Rewrite config.py — add DATABASE_URL, keep MAL/encryption settings

**Files:**
- Modify: `backend/app/core/config.py`

- [ ] **Step 1: Rewrite config.py**

```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str

    # MyAnimeList OAuth credentials
    MAL_CLIENT_ID: str
    MAL_CLIENT_SECRET: str
    ENCRYPTION_KEY: bytes

    # Application URLs
    FRONTEND_URL: str = 'http://localhost:3000'
    BACKEND_URL: str = 'http://localhost:8002'

    DEBUG: bool = False

    model_config = SettingsConfigDict(env_file='.env.backend')


settings = Settings()
```

- [ ] **Step 2: Verify config loads**

```bash
docker-compose run --rm backend python -c "from app.core.config import settings; print(settings.DATABASE_URL)"
```

Expected: `postgresql://ihys:ihys@postgres:5432/ihys`

- [ ] **Step 3: Commit**

```bash
git add backend/app/core/config.py
git commit -m "config: replace supabase settings with DATABASE_URL"
```

---

### Task 5: Rewrite app/db/connection.py using psycopg3

**Files:**
- Modify: `backend/app/db/connection.py`

This is the core task. `DatabaseOperations` methods must produce identical return types to what they did before — dicts (not Row objects) — so callers need no changes.

The Supabase client's `.table(name).select('*').eq(col, val).execute()` pattern maps to plain SQL. psycopg3 uses `row_factory=psycopg.rows.dict_row` to return dicts automatically.

Use a module-level connection pool (`psycopg_pool.ConnectionPool`) so connections are reused across requests — this eliminates per-request connection overhead.

- [ ] **Step 1: Write the new connection.py**

```python
import logging
from typing import Any

import psycopg
import psycopg_pool
from psycopg.rows import dict_row

from app.core.config import settings

logger = logging.getLogger(__name__)

_pool: psycopg_pool.ConnectionPool | None = None


def get_pool() -> psycopg_pool.ConnectionPool:
    global _pool
    if _pool is None:
        _pool = psycopg_pool.ConnectionPool(
            settings.DATABASE_URL,
            kwargs={'row_factory': dict_row},
            min_size=2,
            max_size=10,
        )
    return _pool


class DatabaseOperations:
    def _execute(
        self,
        sql: str,
        params: tuple | None = None,
        *,
        fetch: str = 'one',
    ) -> Any:
        with get_pool().connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params)
                if fetch == 'all':
                    return cur.fetchall()
                if fetch == 'one':
                    return cur.fetchone()
                return None

    def insert_record(self, table_name: str, data: dict) -> dict | None:
        cols = ', '.join(data.keys())
        placeholders = ', '.join(f'%({k})s' for k in data.keys())
        sql = f'INSERT INTO {table_name} ({cols}) VALUES ({placeholders}) RETURNING *'
        return self._execute(sql, data)

    def get_record_by_id(self, table_name: str, record_id: int) -> dict | None:
        sql = f'SELECT * FROM {table_name} WHERE id = %s'
        return self._execute(sql, (record_id,))

    def get_records(
        self,
        table_name: str,
        filters: dict | None = None,
        limit: int | None = None,
    ) -> list[dict]:
        sql = f'SELECT * FROM {table_name}'
        params: list = []
        if filters:
            conditions = ' AND '.join(f'{k} = %s' for k in filters.keys())
            sql += f' WHERE {conditions}'
            params = list(filters.values())
        if limit:
            sql += f' LIMIT {limit}'
        result = self._execute(sql, tuple(params) if params else None, fetch='all')
        return result or []

    def get_records_by_ids(
        self, table_name: str, column: str, ids: list[int]
    ) -> list[dict]:
        if not ids:
            return []
        sql = f'SELECT * FROM {table_name} WHERE {column} = ANY(%s)'
        result = self._execute(sql, (ids,), fetch='all')
        return result or []

    def update_record(
        self, table_name: str, record_id: int, data: dict
    ) -> dict | None:
        assignments = ', '.join(f'{k} = %({k})s' for k in data.keys())
        sql = f'UPDATE {table_name} SET {assignments} WHERE id = %(id)s RETURNING *'
        return self._execute(sql, {**data, 'id': record_id})

    def delete_record(self, table_name: str, record_id: int) -> dict | None:
        sql = f'DELETE FROM {table_name} WHERE id = %s RETURNING *'
        return self._execute(sql, (record_id,))

    def upsert_record(
        self, table_name: str, data: dict, conflict_columns: list[str]
    ) -> dict | None:
        cols = ', '.join(data.keys())
        placeholders = ', '.join(f'%({k})s' for k in data.keys())
        conflict = ', '.join(conflict_columns)
        updates = ', '.join(
            f'{k} = EXCLUDED.{k}'
            for k in data.keys()
            if k not in conflict_columns
        )
        sql = (
            f'INSERT INTO {table_name} ({cols}) VALUES ({placeholders}) '
            f'ON CONFLICT ({conflict}) DO UPDATE SET {updates} RETURNING *'
        )
        return self._execute(sql, data)


db = DatabaseOperations()
```

- [ ] **Step 2: Add psycopg-pool to dependencies**

In `backend/pyproject.toml`, add:

```toml
"psycopg-pool>=3.2.0",
```

Rebuild:

```bash
docker-compose build backend
```

- [ ] **Step 3: Smoke test — start backend and hit an endpoint**

```bash
docker-compose up -d
sleep 5
curl -s http://localhost:8002/health || curl -s http://localhost:8002/
```

Backend should start without import errors.

- [ ] **Step 4: Commit**

```bash
git add backend/app/db/connection.py backend/pyproject.toml
git commit -m "feat: replace supabase client with psycopg3 connection pool"
```

---

### Task 6: Fix upsert_record when all columns are conflict columns

**Files:**
- Modify: `backend/app/db/connection.py`

When all columns are conflict columns (e.g. `character_actors` upsert with `conflict_columns=['character_id','actor_id']` and `data` only has those two keys), `updates` will be empty, causing invalid SQL `DO UPDATE SET`. Use `DO NOTHING` in that case.

- [ ] **Step 1: Update upsert_record**

Replace the `upsert_record` method body:

```python
    def upsert_record(
        self, table_name: str, data: dict, conflict_columns: list[str]
    ) -> dict | None:
        cols = ', '.join(data.keys())
        placeholders = ', '.join(f'%({k})s' for k in data.keys())
        conflict = ', '.join(conflict_columns)
        non_conflict_keys = [k for k in data.keys() if k not in conflict_columns]
        if non_conflict_keys:
            updates = ', '.join(f'{k} = EXCLUDED.{k}' for k in non_conflict_keys)
            on_conflict = f'DO UPDATE SET {updates}'
        else:
            on_conflict = 'DO NOTHING'
        sql = (
            f'INSERT INTO {table_name} ({cols}) VALUES ({placeholders}) '
            f'ON CONFLICT ({conflict}) {on_conflict} RETURNING *'
        )
        return self._execute(sql, data)
```

- [ ] **Step 2: Test upsert with a character_actors-style call**

```bash
docker-compose exec backend python -c "
from app.db.connection import db
# Should not raise
result = db.upsert_record('actors', {'name': '__test__', 'photo': ''}, ['name'])
print('upsert ok:', result)
db.delete_record('actors', result['id'])
print('cleanup ok')
"
```

Expected: prints the upserted row then confirms deletion.

- [ ] **Step 3: Commit**

```bash
git add backend/app/db/connection.py
git commit -m "fix: upsert_record DO NOTHING when no non-conflict columns"
```

---

### Task 7: End-to-end verification

- [ ] **Step 1: Bring up full stack**

```bash
docker-compose up -d
```

- [ ] **Step 2: Check backend logs for errors**

```bash
docker-compose logs backend --tail=50
```

Expected: no import errors, uvicorn listening on 0.0.0.0:8000.

- [ ] **Step 3: Measure query latency**

```bash
docker-compose exec backend python -c "
from app.db.connection import db
import time

t=time.time(); db.get_records('anime', {}); print(f'First:  {time.time()-t:.3f}s')
t=time.time(); db.get_records('anime', {}); print(f'Second: {time.time()-t:.3f}s')
t=time.time(); db.get_records('anime', {}); print(f'Third:  {time.time()-t:.3f}s')
"
```

Expected: all three under 5ms.

- [ ] **Step 4: Run backend linter**

```bash
docker-compose exec backend ruff check .
docker-compose exec backend mypy .
```

Expected: no errors.

- [ ] **Step 5: Run existing tests**

```bash
docker-compose exec backend pytest
```

Expected: all pass (tests use mocks, not live DB).

- [ ] **Step 6: Remove stale Supabase env vars from .env.backend**

Remove these lines (they are no longer read by config.py):
```
SUPABASE_URL=...
SUPABASE_SECRET_KEY=...
SUPABASE_SERVICE_KEY=...
SUPABASE_PUBLISHABLE_KEY=...
SUPABASE_ANON_KEY=...
SUPABASE_PASS=...
```

- [ ] **Step 7: Final commit**

```bash
git add .env.backend
git commit -m "chore: remove unused supabase env vars"
```
