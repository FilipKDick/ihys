# Observability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Sentry error tracking (cloud) and Umami analytics (self-hosted) to the stack.

**Architecture:** Sentry is initialised in FastAPI and Nuxt via DSN env vars — no-op when vars are absent. Umami runs as two new Docker containers (app + its own Postgres) behind Caddy at `analytics.{DOMAIN}`. The Nuxt frontend injects the Umami tracking script via `useHead` only when the website ID env var is set.

**Tech Stack:** `sentry-sdk[fastapi]` (Python), `@sentry/nuxt` (Nuxt 4), `ghcr.io/umami-software/umami:postgresql-latest`, Caddy, Docker Compose.

---

### Task 1: Add Sentry to the FastAPI backend

**Files:**
- Modify: `backend/pyproject.toml`
- Modify: `backend/app/core/config.py`
- Modify: `backend/app/main.py`
- Modify: `.env.backend.dist`

- [ ] **Step 1: Add `sentry-sdk` to pyproject.toml**

In `backend/pyproject.toml`, add to the `dependencies` list:

```toml
"sentry-sdk[fastapi]>=2.0.0",
```

- [ ] **Step 2: Add optional SENTRY_DSN to config**

Edit `backend/app/core/config.py`:

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

    # Observability — optional, disabled when unset
    SENTRY_DSN: str | None = None

    model_config = SettingsConfigDict(env_file='.env.backend')


settings = Settings()
```

- [ ] **Step 3: Initialise Sentry in main.py**

Edit `backend/app/main.py`:

```python
import sentry_sdk
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sentry_sdk.integrations.fastapi import FastApiIntegration
from starlette.middleware.sessions import SessionMiddleware

from app.api import anime, auth, user_anime
from app.core.config import settings

if settings.SENTRY_DSN:
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        integrations=[FastApiIntegration()],
        traces_sample_rate=0.1,
        send_default_pii=False,
    )

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

- [ ] **Step 4: Document SENTRY_DSN in .env.backend.dist**

Add to `.env.backend.dist`:

```env
# Sentry error tracking — leave empty to disable (safe for local dev)
# Get DSN from: https://sentry.io → Your Project → Settings → Client Keys
SENTRY_DSN=
```

- [ ] **Step 5: Install the new dependency inside the container and verify the backend starts**

```bash
docker compose build backend
docker compose up backend -d
docker compose exec backend python -c "import sentry_sdk; print('sentry ok')"
```

Expected: `sentry ok` printed, no errors.

- [ ] **Step 6: Commit**

```bash
git add backend/pyproject.toml backend/app/core/config.py backend/app/main.py .env.backend.dist
git commit -m "feat: add Sentry error tracking to FastAPI backend"
```

---

### Task 2: Add Sentry to the Nuxt 4 frontend

**Files:**
- Modify: `frontend/package.json` (via npm install)
- Modify: `frontend/nuxt.config.ts`
- Modify: `.env.frontend.dist`

- [ ] **Step 1: Install @sentry/nuxt**

```bash
cd frontend && npm install @sentry/nuxt
```

- [ ] **Step 2: Add Sentry module to nuxt.config.ts**

Edit `frontend/nuxt.config.ts`:

```typescript
// https://nuxt.com/docs/api/configuration/nuxt-config
export default defineNuxtConfig({
  compatibilityDate: '2025-05-15',
  devtools: { enabled: process.env.NODE_ENV !== 'production' },

  modules: [
    '@nuxt/eslint',
    '@nuxt/fonts',
    '@nuxt/icon',
    '@nuxt/image',
    '@nuxt/ui',
    '@sentry/nuxt/module'
  ],
  css: ['~/assets/css/main.css'],
  runtimeConfig: {
    public: {
      apiBase: process.env.NUXT_PUBLIC_API_BASE_URL || '',
      sentryDsn: process.env.NUXT_PUBLIC_SENTRY_DSN || '',
      umamiWebsiteId: process.env.NUXT_PUBLIC_UMAMI_WEBSITE_ID || '',
      umamiScriptUrl: process.env.NUXT_PUBLIC_UMAMI_SCRIPT_URL || '',
    }
  },
  sentry: {
    sourceMapsUploadOptions: {
      org: '',   // fill in your Sentry org slug
      project: '', // fill in your Sentry project slug
    }
  }
})
```

- [ ] **Step 3: Create sentry.client.config.ts**

Create `frontend/sentry.client.config.ts`:

```typescript
import * as Sentry from '@sentry/nuxt'

const config = useRuntimeConfig()

if (config.public.sentryDsn) {
  Sentry.init({
    dsn: config.public.sentryDsn,
    tracesSampleRate: 0.1,
  })
}
```

- [ ] **Step 4: Document env var in .env.frontend.dist**

Add to `.env.frontend.dist`:

```env
# Sentry error tracking — leave empty to disable (safe for local dev)
# Get DSN from: https://sentry.io → Your Project → Settings → Client Keys
NUXT_PUBLIC_SENTRY_DSN=
```

- [ ] **Step 5: Verify frontend builds**

```bash
cd frontend && npm run build
```

Expected: build completes with no errors.

- [ ] **Step 6: Commit**

```bash
git add frontend/package.json frontend/package-lock.json frontend/nuxt.config.ts frontend/sentry.client.config.ts .env.frontend.dist
git commit -m "feat: add Sentry error tracking to Nuxt frontend"
```

---

### Task 3: Add Umami env vars and Docker services

**Files:**
- Modify: `.env.dist`
- Modify: `.env.backend.dist` (no change needed — Umami has no backend integration)
- Modify: `compose.yml`

- [ ] **Step 1: Add Umami vars to .env.dist**

Add to `.env.dist`:

```env
# Umami analytics (self-hosted)
UMAMI_POSTGRES_DB=umami
UMAMI_POSTGRES_USER=umami
UMAMI_POSTGRES_PASSWORD=CHANGE_ME
# Random string used by Umami to sign JWTs — generate with:
# python3 -c "import secrets; print(secrets.token_hex(32))"
UMAMI_APP_SECRET=CHANGE_ME
```

- [ ] **Step 2: Add Umami containers to compose.yml**

Edit `compose.yml` — add two new services after the existing `postgres` service, before `backend`:

```yaml
  umami_postgres:
    image: postgres:17
    container_name: ihys_umami_postgres
    restart: unless-stopped
    environment:
      POSTGRES_DB: ${UMAMI_POSTGRES_DB}
      POSTGRES_USER: ${UMAMI_POSTGRES_USER}
      POSTGRES_PASSWORD: ${UMAMI_POSTGRES_PASSWORD}
    volumes:
      - umami_postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${UMAMI_POSTGRES_USER} -d ${UMAMI_POSTGRES_DB}"]
      interval: 5s
      timeout: 5s
      retries: 10

  umami:
    image: ghcr.io/umami-software/umami:postgresql-latest
    container_name: ihys_umami
    restart: unless-stopped
    environment:
      DATABASE_URL: postgresql://${UMAMI_POSTGRES_USER}:${UMAMI_POSTGRES_PASSWORD}@umami_postgres:5432/${UMAMI_POSTGRES_DB}
      APP_SECRET: ${UMAMI_APP_SECRET}
    depends_on:
      umami_postgres:
        condition: service_healthy
```

Also add `umami_postgres_data` to the `volumes` block at the bottom of `compose.yml`:

```yaml
volumes:
  postgres_data:
  umami_postgres_data:
  caddy_data:
  caddy_config:
```

- [ ] **Step 3: Verify compose config is valid**

```bash
docker compose config --quiet
```

Expected: no output (silent success means valid).

- [ ] **Step 4: Commit**

```bash
git add .env.dist compose.yml
git commit -m "feat: add Umami and its Postgres to Docker Compose"
```

---

### Task 4: Route Umami through Caddy

**Files:**
- Modify: `Caddyfile`

- [ ] **Step 1: Add analytics subdomain to Caddyfile**

Edit `Caddyfile`:

```
www.{$DOMAIN} {
    redir https://{$DOMAIN}{uri} permanent
}

{$DOMAIN} {
    # Backend API
    reverse_proxy /api/* backend:8000

    # Frontend
    reverse_proxy * frontend:3000
}

analytics.{$DOMAIN} {
    reverse_proxy umami:3000
}
```

- [ ] **Step 2: Commit**

```bash
git add Caddyfile
git commit -m "feat: route analytics subdomain to Umami via Caddy"
```

---

### Task 5: Add Umami tracking script to Nuxt frontend

**Files:**
- Modify: `frontend/app.vue`
- Modify: `.env.frontend.dist`

- [ ] **Step 1: Add Umami env vars to .env.frontend.dist**

Add to `.env.frontend.dist`:

```env
# Umami analytics tracking — leave empty to disable (safe for local dev)
# Get NUXT_PUBLIC_UMAMI_WEBSITE_ID from Umami admin UI after adding your site
NUXT_PUBLIC_UMAMI_WEBSITE_ID=
# Full URL to your Umami script, e.g. https://analytics.yourdomain.com/script.js
NUXT_PUBLIC_UMAMI_SCRIPT_URL=
```

- [ ] **Step 2: Inject tracking script in app.vue**

Edit `frontend/app.vue`:

```vue
<template>
  <NuxtRouteAnnouncer />
  <NuxtPage />
</template>

<script setup lang="ts">
const config = useRuntimeConfig()

if (config.public.umamiWebsiteId && config.public.umamiScriptUrl) {
  useHead({
    script: [
      {
        src: config.public.umamiScriptUrl,
        defer: true,
        'data-website-id': config.public.umamiWebsiteId,
      },
    ],
  })
}
</script>
```

- [ ] **Step 3: Verify frontend builds**

```bash
cd frontend && npm run build
```

Expected: build completes with no errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/app.vue .env.frontend.dist
git commit -m "feat: inject Umami tracking script in Nuxt app"
```

---

### Task 6: First-run setup guide (manual steps)

This task is documentation-only — no code changes. These steps must be done once after deploying.

- [ ] **Step 1: Copy and fill env files if not already done**

```bash
cp .env.dist .env          # fill UMAMI_POSTGRES_PASSWORD and UMAMI_APP_SECRET
cp .env.frontend.dist .env.frontend
cp .env.backend.dist .env.backend
```

- [ ] **Step 2: Create Sentry projects**

1. Go to https://sentry.io and create a free account.
2. Create a project: Platform = **FastAPI** (under Python). Copy the DSN into `SENTRY_DSN` in `.env.backend`.
3. Create a second project: Platform = **Nuxt**. Copy the DSN into `NUXT_PUBLIC_SENTRY_DSN` in `.env.frontend`.

- [ ] **Step 3: Deploy the stack**

```bash
DOCKER_TARGET=prod docker compose up -d --build
```

Caddy will obtain TLS certificates for `yourdomain.com` and `analytics.yourdomain.com` automatically.

- [ ] **Step 4: Set up Umami**

1. Visit `https://analytics.yourdomain.com`.
2. Log in with default credentials: username `admin`, password `umami`.
3. **Immediately change the password** (top-right menu → Profile).
4. Go to Settings → Websites → Add website. Enter your site name and domain.
5. Copy the **Website ID** (UUID) shown after creation.
6. Set `NUXT_PUBLIC_UMAMI_WEBSITE_ID=<that UUID>` in `.env.frontend`.
7. Set `NUXT_PUBLIC_UMAMI_SCRIPT_URL=https://analytics.yourdomain.com/script.js` in `.env.frontend`.
8. Redeploy the frontend to pick up the new vars:

```bash
DOCKER_TARGET=prod docker compose up -d --build frontend
```

- [ ] **Step 5: Verify Sentry is receiving errors**

Visit `https://yourdomain.com` in a browser. Then in your Sentry dashboard, check the **Issues** tab — you should see at least one event (Sentry sends a test event on first init). Alternatively trigger a test error via the backend debug route if you add one.

- [ ] **Step 6: Verify Umami is tracking**

Visit `https://yourdomain.com`. Go to `https://analytics.yourdomain.com` → your site → Realtime. You should see yourself as an active visitor within a few seconds.
