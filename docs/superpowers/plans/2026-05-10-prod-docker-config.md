# Production Docker Configuration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Harden compose.yml and env dist files for production deployment behind an existing reverse proxy.

**Architecture:** No new containers. Backend and frontend ports are bound to 127.0.0.1 only so the host reverse proxy can reach them but the internet cannot. Dev-only volume mounts are removed from the prod path. Env dist files are updated to reflect the actual config vars the app uses.

**Tech Stack:** Docker Compose, bash

---

### Task 1: Bind backend and frontend ports to localhost only in compose.yml

**Files:**
- Modify: `compose.yml`

- [ ] **Step 1: Update backend port binding**

In `compose.yml`, change the backend `ports` entry from:
```yaml
ports:
  - "8002:8000"
```
to:
```yaml
ports:
  - "127.0.0.1:8000:8000"
```
Note: port changed from 8002 to 8000 — the reverse proxy will connect directly on 8000. If you need to keep 8002 for local dev habits, use `127.0.0.1:8002:8000` instead, but the spec uses 8000.

- [ ] **Step 2: Update frontend port binding**

Change the frontend `ports` entry from:
```yaml
ports:
  - "3000:3000"
```
to:
```yaml
ports:
  - "127.0.0.1:3000:3000"
```

- [ ] **Step 3: Update postgres port binding**

Change the postgres `ports` entry from:
```yaml
ports:
  - "5433:5432"
```
to:
```yaml
ports:
  - "127.0.0.1:5433:5432"
```

- [ ] **Step 4: Verify compose.yml is valid**

```bash
docker compose config --quiet && echo "valid"
```
Expected output: `valid`

- [ ] **Step 5: Commit**

```bash
git add compose.yml
git commit -m "fix: bind all container ports to 127.0.0.1 for production"
```

---

### Task 2: Remove dev-only volume mounts from backend and frontend

**Files:**
- Modify: `compose.yml`

In dev, `./backend:/app` is mounted so code changes are picked up without rebuilding. In prod (target=prod), the code is baked into the image — these mounts override and break it by replacing the image's `/app` with the local source tree. Remove them.

- [ ] **Step 1: Remove backend dev volumes**

In `compose.yml`, remove the entire `volumes` block under the `backend` service:
```yaml
# DELETE THIS:
volumes:
  - ./backend:/app
```
The backend service should have no `volumes` key after this change.

- [ ] **Step 2: Remove frontend dev volumes**

In `compose.yml`, remove the entire `volumes` block under the `frontend` service:
```yaml
# DELETE THIS:
volumes:
  - ./frontend:/app
  - /app/node_modules
  - /app/.nuxt
```
The frontend service should have no `volumes` key after this change.

- [ ] **Step 3: Verify compose.yml is valid**

```bash
docker compose config --quiet && echo "valid"
```
Expected output: `valid`

- [ ] **Step 4: Verify postgres volume is still present**

```bash
docker compose config | grep -A3 "postgres_data"
```
Expected: shows `postgres_data` volume definition under both the `postgres` service and the top-level `volumes` block.

- [ ] **Step 5: Commit**

```bash
git add compose.yml
git commit -m "fix: remove dev volume mounts from backend and frontend services"
```

---

### Task 3: Fix .env.backend.dist

**Files:**
- Modify: `.env.backend.dist`

The current dist file has Supabase vars (`SUPABASE_URL`, `SUPABASE_SECRET_KEY`, `SUPABASE_PUBLISHABLE_KEY`) that the app no longer uses. Replace with the vars `backend/app/core/config.py` actually reads.

- [ ] **Step 1: Replace .env.backend.dist contents**

Write the file with exactly this content:
```
# PostgreSQL connection string — postgres service is on the Docker internal network
DATABASE_URL=postgresql://ihys:<password>@postgres:5432/ihys

# MyAnimeList OAuth credentials (get from https://myanimelist.net/apiconfig)
MAL_CLIENT_ID=your_mal_client_id
MAL_CLIENT_SECRET=your_mal_client_secret

# Fernet encryption key for storing MAL OAuth tokens
# Generate with: python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
ENCRYPTION_KEY=your_fernet_key_here

# URL of the frontend — used for CORS allow_origins
FRONTEND_URL=https://yourdomain.com

# Set to False in production
DEBUG=False
```

- [ ] **Step 2: Commit**

```bash
git add .env.backend.dist
git commit -m "fix: update .env.backend.dist to match actual config vars (replace Supabase vars with DATABASE_URL)"
```

---

### Task 4: Fix .env.frontend.dist

**Files:**
- Modify: `.env.frontend.dist`

The current value `http://localhost:8002` is a hardcoded dev URL. In prod, the frontend is served on the same domain as the backend (via reverse proxy), so a relative `/api` path is correct — no domain needed.

- [ ] **Step 1: Replace .env.frontend.dist contents**

Write the file with exactly this content:
```
# Relative path — the reverse proxy routes /api/* to the backend on the same domain.
# Do not use an absolute URL here; it would break if the domain changes.
NUXT_PUBLIC_API_BASE_URL=/api
```

- [ ] **Step 2: Commit**

```bash
git add .env.frontend.dist
git commit -m "fix: set NUXT_PUBLIC_API_BASE_URL to relative /api path for same-domain reverse proxy"
```

---

### Task 5: Smoke test the prod build locally

This task verifies the prod images build and start correctly. It does not require a real domain or TLS.

- [ ] **Step 1: Build prod images**

```bash
DOCKER_TARGET=prod docker compose build 2>&1 | tail -5
```
Expected: no errors, both `backend` and `frontend` images built successfully.

- [ ] **Step 2: Start prod stack**

```bash
DOCKER_TARGET=prod docker compose up -d
```

- [ ] **Step 3: Verify all containers are running**

```bash
docker compose ps
```
Expected: `ihys_postgres`, `ihys_backend`, `ihys_frontend` all show `running` or `Up`.

- [ ] **Step 4: Verify backend is reachable on localhost**

```bash
curl -s http://127.0.0.1:8000/health 2>&1 || curl -s http://127.0.0.1:8000/docs 2>&1 | head -3
```
Expected: some HTTP response (200 or HTML), not "connection refused".

- [ ] **Step 5: Verify frontend is reachable on localhost**

```bash
curl -s http://127.0.0.1:3000 2>&1 | head -3
```
Expected: HTML response, not "connection refused".

- [ ] **Step 6: Verify postgres port is NOT accessible externally**

This can only be fully verified on the server. Locally, just confirm it's bound to 127.0.0.1:

```bash
docker compose port postgres 5432
```
Expected: `0.0.0.0:5433` or `127.0.0.1:5433` — if running locally. On the server, confirm with `ss -tlnp | grep 5433`.

- [ ] **Step 7: Tear down**

```bash
docker compose down
```
