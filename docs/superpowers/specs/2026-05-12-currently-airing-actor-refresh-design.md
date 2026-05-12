---
name: currently-airing-actor-refresh
description: Refresh voice actor/character data for currently-airing anime on every user sync
metadata:
  type: project
---

## Problem

Character data is only scraped once per anime. For currently-airing shows, new voice actors are cast every week as new episodes air, but the DB is never updated after the initial scrape.

Additionally, the current sync re-scrapes every anime unconditionally on every sync — including finished shows — which is wasteful and means `skipped_count` is always 0.

## Solution

Modify `sync_actor_data_for_anime` in `backend/app/services/mal_api.py` to branch on airing status:

- **Currently airing** (`status == 'currently_airing'` or `'Currently Airing'`): always call `fetch_actor_data` — unconditional re-scrape picks up new weekly cast additions.
- **Everything else** (finished, not yet aired): skip if characters already exist in DB. Uses the same logic as `ensure_actor_data`.

The `anime['status']` field is already present on every anime dict returned from the DB, populated from the MAL API during sync. Both the MAL API format (`currently_airing`) and the HTML scraper format (`Currently Airing`) must be handled.

## Scope

Single function change in `mal_api.py:sync_actor_data_for_anime`. No schema changes, no new endpoints, no new services.

## Outcome

- Currently-airing anime: characters refreshed on every user sync.
- Finished anime: scraped once, then skipped (no re-scraping on subsequent syncs).
- `skipped_count` in sync stats becomes accurate.
