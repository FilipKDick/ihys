# Agent Guidelines for Who's That Seiyuu

## Purpose

Who's That Seiyuu helps a user's girlfriend discover shared voice actors across anime. When she starts watching a new anime, she wants to know which voice actors in it she's already heard — i.e., which actors also voiced characters in animes she's previously watched. MAL has this data but it's not surfaced in a user-friendly way, so this app aggregates it and shows the overlap.

## Build/Test/Lint Commands

Backend commands run inside the Docker container:
- Backend: `docker-compose exec backend ruff check .` (lint), `docker-compose exec backend ruff format .` (format), `docker-compose exec backend mypy .` (type check)
- Frontend: `cd frontend && npm run dev` (dev), `npm run build` (build), `npm run lint` (lint)
- Docker: `docker-compose up` (run services), `DOCKER_TARGET=prod docker-compose up` (production)
- Pre-commit: `pre-commit run --all-files` (run all checks)

## General Guidelines
- Do not add unnecessary comments; code should be self-explanatory.
- Do not wrap everything in try/except; handle exceptions only where necessary.
- This project uses docker, so ensure your code works within the containerized environment.

## Python Code Style (Backend)
- Line length: 88 characters
- Python 3.13+
- Use single quotes for strings (ruff configured)
- Import style: separate stdlib/third-party/local imports with blank lines
- Type hints required on all function definitions (mypy strict mode); 
  - prefer | None for optional types
  - dict instead of Dict
- Use pydantic-settings for configuration classes
- FastAPI async/await patterns for handlers
- Error handling: raise HTTPException for API errors

## TypeScript/Vue Code Style (Frontend)
- Nuxt 3 + Vue 3 composition API
- Use TypeScript strict mode
- ESLint with Nuxt defaults
- Component naming: PascalCase for files
- Composables in `composables/` directory

## Project Structure
- `backend/`: FastAPI Python backend with Supabase
- `frontend/`: Nuxt 3 TypeScript frontend
- Monorepo with Docker Compose for local development