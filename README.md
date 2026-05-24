# Who's That Seiyuu?

Discover shared voice actors between anime. When starting a new show, Who's That Seiyuu tells you which voice actors you've already heard — actors who voiced characters in anime on your watchlist.

Data is pulled from [MyAnimeList](https://myanimelist.net). Auth is OAuth via MAL.

---

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) with Compose v2 (`docker compose` not `docker-compose`)
- A [MyAnimeList API application](https://myanimelist.net/apiconfig) (free, takes ~2 minutes to create)
- Python 3.13+ — only needed locally to generate the encryption key

---

## First-time setup

### 1. Clone

```bash
git clone <repo-url>
cd ihys
```

### 2. Create a MAL API application

Go to https://myanimelist.net/apiconfig and create a new application:

- **App Type:** Web
- **App Redirect URL:** `http://localhost:8002/api/auth/callback` (dev) or `https://yourdomain.com/api/auth/callback` (prod)

Note your **Client ID** and **Client Secret**.

### 3. Generate an encryption key

The app encrypts MAL OAuth tokens at rest using Fernet. Generate a key once:

```bash
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Keep this key safe — losing it means all stored tokens become unreadable.

### 4. Configure Postgres credentials

```bash
cp .env.dist .env
```

Edit `.env` — this file is auto-loaded by Docker Compose for variable substitution in `compose.yml`:

```env
POSTGRES_DB=ihys
POSTGRES_USER=ihys
POSTGRES_PASSWORD=choose_a_strong_password
```

### 5. Configure the backend

```bash
cp .env.backend.dist .env.backend
```

Edit `.env.backend`:

```env
DATABASE_URL=postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB}
MAL_CLIENT_ID=<your MAL client ID>
MAL_CLIENT_SECRET=<your MAL client secret>
ENCRYPTION_KEY=<key from step 3>
FRONTEND_URL=http://localhost:3000                        # dev default
BACKEND_URL=http://localhost:8002                         # dev default
DEBUG=True
```

> The `${...}` vars are resolved from `.env` at runtime — you don't need to hardcode the password here.

### 6. Configure the frontend

```bash
cp .env.frontend.dist .env.frontend
```

Edit `.env.frontend`:

```env
NUXT_PUBLIC_API_BASE_URL=   # leave empty; fetch calls already use /api/* paths
```

---

## Running locally (dev)

```bash
docker compose up
```

- Frontend: http://localhost:3000
- Backend API docs: http://localhost:8002/docs
- Postgres: `localhost:5433` (credentials from your `.env`)

Code changes are picked up automatically — the backend uses `--reload` and the frontend uses Nuxt dev server with HMR. No rebuild needed.

---

## Running in production

### 1. Fill in env files with production values

`.env`:
```env
POSTGRES_DB=ihys
POSTGRES_USER=ihys
POSTGRES_PASSWORD=choose_a_strong_password
```

`.env.backend`:
```env
DATABASE_URL=postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB}
MAL_CLIENT_ID=<your MAL client ID>
MAL_CLIENT_SECRET=<your MAL client secret>
ENCRYPTION_KEY=<key from first-time setup>
FRONTEND_URL=https://${DOMAIN}
BACKEND_URL=https://${DOMAIN}
DEBUG=False
```

`.env.frontend`:
```env
NUXT_PUBLIC_API_BASE_URL=
NODE_ENV=production
```

> `NODE_ENV=production` is required to disable Nuxt devtools. Without it the debug toolbar will appear in the browser.
> `NUXT_PUBLIC_API_BASE_URL` must be empty in production — fetch calls already include `/api/*` paths, and the reverse proxy handles routing. Setting it to `/api` causes double `/api/api/...` URLs.

### 2. Start

### Shared Proxy Network

Production ingress expects the external Docker network `caddy-shared` to exist:

```bash
docker network create caddy-shared
```

The command is safe to skip if the network already exists.

```bash
DOCKER_TARGET=prod docker compose up -d --build
```

Public HTTPS ingress is owned by the sibling `server-infra` repository. Start this app first, then start or reload `server-infra` so Caddy can route to `ihys_frontend` and `ihys_backend` on the shared `caddy-shared` Docker network.

### 3. MAL OAuth callback

Register `https://yourdomain.com/api/auth/callback` as the redirect URL in your [MAL API application](https://myanimelist.net/apiconfig).

---

## Database migrations

Migrations in `migrations/` are applied automatically on **first volume init** via `docker-entrypoint-initdb.d`. They do not re-run on subsequent starts.

To apply a new migration manually:

```bash
docker compose exec postgres psql -U ${POSTGRES_USER} -d ${POSTGRES_DB} -f /dev/stdin < migrations/your_migration.sql
```

---

## Useful commands

```bash
# View logs
docker compose logs -f backend
docker compose logs -f frontend

# Run backend tests
docker compose exec backend pytest -v

# Lint backend
docker compose exec backend ruff check .

# Connect to Postgres
psql postgresql://ihys:ihys@localhost:5433/ihys

# Stop everything
docker compose down

# Stop and wipe database
docker compose down -v
```

---

## Tech stack

| Layer | Technology |
|---|---|
| Frontend | Nuxt 4, Vue 3, TypeScript, Tailwind (@nuxt/ui) |
| Backend | FastAPI, Python 3.13, psycopg3 |
| Database | PostgreSQL 17 |
| Auth | MAL OAuth 2.0 (PKCE), server-side sessions |
| Scraping | BeautifulSoup (MAL character pages) |
| Container | Docker Compose |
