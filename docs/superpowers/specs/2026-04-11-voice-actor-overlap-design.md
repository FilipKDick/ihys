# IHYS — Voice Actor Overlap Feature Design

**Date:** 2026-04-11

## Purpose

Help users discover shared voice actors between a new anime they're watching and their existing watch history. MAL has this data but doesn't surface it conveniently. IHYS aggregates it and shows the overlap in one view. Supports multiple user accounts.

## Core User Flow

1. User logs in via MAL OAuth
2. App syncs their watched anime list from MAL into local DB (`user_anime` table)
3. User types an anime name → search hits MAL API and returns matching titles
4. User picks one → backend checks if that MAL ID exists in the local `anime` table:
   - **Found** → use existing actor/character data from DB
   - **Not found** → scrape MAL for that anime's characters and voice actors, store in DB, then proceed
5. Backend queries shared actors: actors who appear in the selected anime AND in any anime in the user's watch history
6. Frontend shows results as actor cards (actor photo, character name in the searched anime, tags for each watched anime they appeared in)

## Backend — New API Endpoints

| Endpoint | Description |
|---|---|
| `GET /api/anime/search?q=<name>` | Searches MAL API by name, returns title + MAL ID + cover image |
| `GET /api/anime/{mal_id}/actors` | Ensures anime data is in DB (scrapes on-demand if not), returns characters + actors |
| `GET /api/user/anime/{mal_id}/overlap` | Core endpoint — returns actors in the given anime who also appear in the authenticated user's watch history |

The overlap query joins `character_actors`, `characters`, `user_anime`, and `anime` tables — all already exist in the schema.

## Data Pipeline

- **Watch history** — stored in `user_anime`, synced from MAL on demand
- **Anime metadata + actors** — stored in `anime`, `characters`, `actors`, `character_actors`; populated on first lookup via existing BeautifulSoup scrapers
- **MAL API** — used only for name search (autocomplete) and on-demand scraping; not hit on repeat lookups

On-demand scraping strategy: if the searched anime isn't in DB, scrape inline (blocking, a few seconds). Results are cached permanently. A queue-based approach can replace this later if latency becomes a problem.

## Frontend — 4 Screens

1. **Login** — single MAL OAuth button
2. **Home** — search bar (searches any anime by name), sync button, scrollable watch history list showing anime title + watch status
3. **Search dropdown** — live autocomplete as user types, showing title + year from MAL API
4. **Overlap results** — selected anime cover + title, list of shared actor cards each showing: actor photo, actor name, character they voice in the searched anime, tags for each watched anime they appeared in

## Error Handling

- **Scrape fails / MAL unreachable** → return an error message to the frontend ("couldn't fetch actor data, try again"), don't crash
- **No shared actors found** → return empty array, frontend shows explicit "no shared voice actors found" message

## What's Already Built

- MAL OAuth 2.0 PKCE login + session management
- `user_anime` CRUD + MAL list sync (`/api/user/anime/sync`)
- Full DB schema: `anime`, `characters`, `actors`, `character_actors`, `user_anime`
- BeautifulSoup scrapers for anime metadata and character/actor data
- Nuxt 3 + Vue 3 frontend scaffold

## What Needs to Be Built

**Backend:**
- `GET /api/anime/search` — MAL API name search
- `GET /api/anime/{mal_id}/actors` — on-demand scrape + return actors
- `GET /api/user/anime/{mal_id}/overlap` — shared actor query
- Wire scraper into the API (currently only run as CLI)

**Frontend:**
- Login page
- Home page with search bar + watch list + sync button
- Search autocomplete dropdown
- Overlap results page
