# Production Docker Configuration — Design Spec

**Date:** 2026-05-10  
**Status:** Approved

## Goal

Harden the Docker Compose setup for production deployment on a VPS that already has a reverse proxy (nginx/Caddy/etc.) handling TLS and routing. No new proxy container is added.

## Routing assumption

The external reverse proxy routes:
- `yourdomain.com/api/*` → `localhost:8000` (backend)  
- `yourdomain.com/*` → `localhost:3000` (frontend)

Because everything is same-domain, CORS is a non-issue for browser requests.

## Changes

### `compose.yml`

**Backend:**
- Remove host port mapping (`8002:8000`). The reverse proxy reaches backend via the Docker host network (`localhost:8000`) or directly if using `network_mode: host`. Since the reverse proxy runs on the host (not in Docker), the port must still be bound — but only to `127.0.0.1:8000` to block internet access.
- Remove `volumes` dev mount (`./backend:/app`) — not needed in prod; code is baked into the image.

**Frontend:**
- Remove host port mapping (`3000:3000`) → bind to `127.0.0.1:3000`.
- Remove dev `volumes` mounts (`./frontend:/app`, `/app/node_modules`, `/app/.nuxt`).

**Postgres:**
- Keep containerized with `postgres_data` named volume — no change to data storage.
- Change host port binding from `5433:5432` → `127.0.0.1:5433:5432` so it's reachable from the host for debugging but not from the internet.
- Internal services continue to reach it as `postgres:5432` via the Docker network — no change needed in `DATABASE_URL`.

**General:**
- `DOCKER_TARGET=prod docker compose up -d --build` activates the prod Dockerfile targets, which bake in code and skip hot-reload.

### `.env.backend.dist`

Replace Supabase placeholder vars with the actual vars the app uses:

```
DATABASE_URL=postgresql://ihys:<password>@postgres:5432/ihys
MAL_CLIENT_ID=...
MAL_CLIENT_SECRET=...
ENCRYPTION_KEY=<Fernet key — generate with: python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())">
FRONTEND_URL=https://yourdomain.com
DEBUG=False
```

### `.env.frontend.dist`

Change `NUXT_PUBLIC_API_BASE_URL` to a relative path so it works regardless of domain:

```
NUXT_PUBLIC_API_BASE_URL=/api
```

The reverse proxy strips `/api` and forwards to the backend, so this is correct as-is — no domain hardcoding needed.

## What does NOT change

- Postgres volume (`postgres_data`) — data persists across deploys
- Backend `prod` Dockerfile target — already correct (copies code, no `--reload`)
- Frontend `prod` Dockerfile target — already correct (builds `.output`, runs with node)
- Migration strategy — `docker-entrypoint-initdb.d` runs on first volume init only; new migrations applied manually

## Deployment procedure (for reference)

```bash
git pull
cp .env.backend.dist .env.backend   # fill in real values
cp .env.frontend.dist .env.frontend
DOCKER_TARGET=prod docker compose up -d --build
docker compose ps  # verify all healthy
```
