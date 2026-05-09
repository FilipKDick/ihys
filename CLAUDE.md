# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Purpose

IHYS helps a user's girlfriend discover shared voice actors across anime. When she starts watching a new anime, she wants to know which voice actors in it she's already heard — i.e., which actors also voiced characters in animes she's previously watched. MAL has this data but it's not surfaced in a user-friendly way, so this app aggregates it and shows the overlap.

## Commands

Backend commands run inside the Docker container:

```bash
# Backend (run inside container)
docker-compose exec backend ruff check .    # Lint
docker-compose exec backend ruff format .   # Format
docker-compose exec backend mypy .          # Type check

# Frontend
cd frontend && npm run dev        # Dev server
cd frontend && npm run build      # Build
cd frontend && npm run lint       # ESLint

# Full stack (dev with auto-reload)
docker-compose up

# Production
DOCKER_TARGET=prod docker-compose up

# Pre-commit
pre-commit run --all-files
```

There is no test suite currently.

## Architecture

IHYS is an anime watchlist app with MAL (MyAnimeList) OAuth integration. Monorepo with a FastAPI backend and Nuxt 3 frontend, both containerized via Docker Compose.

### Backend (`backend/`)

FastAPI app with Supabase (PostgreSQL) as the database. Key areas:

- **`app/api/`** — Route handlers. `auth.py` handles MAL OAuth login/callback; `user_anime.py` handles CRUD for user anime lists.
- **`app/services/`** — Business logic. `mal_api.py` syncs lists from the MAL API v2; `auth.py` manages sessions; `security.py` encrypts/decrypts MAL OAuth tokens with Fernet; `anime_download.py` fetches anime metadata.
- **`app/db/`** — `connection.py` has the Supabase client and `DatabaseOperations` class; `models.py` has Pydantic models for DB entities (User, Anime, Character, etc.); `base.py` has the `DataBaseModel` base class with upsert support.
- **`app/serializers.py`** — Request/response schemas (separate from DB models).
- **`scrapers/`** — BeautifulSoup scrapers that pull anime metadata from MAL web pages.

**Auth flow:** OAuth PKCE → MAL callback → tokens encrypted and stored in Supabase → session ID in httponly cookie.

### Frontend (`frontend/`)

Nuxt 3 + Vue 3 Composition API + TypeScript. Communicates with the backend API (configured via `NUXT_PUBLIC_API_BASE` env var, defaults to `http://localhost:8002`).

## Code Style

### Python
- Python 3.13+, line length 88, single quotes
- Type hints required everywhere; use `X | None` not `Optional[X]`, `dict` not `Dict`
- Import groups: stdlib / third-party / local, separated by blank lines
- Raise `HTTPException` for API errors; don't wrap everything in try/except

### TypeScript/Vue
- Vue 3 Composition API, TypeScript strict mode
- PascalCase component filenames
- Composables go in `composables/`
