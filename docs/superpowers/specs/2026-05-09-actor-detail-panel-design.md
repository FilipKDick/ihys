# Actor Detail Panel — Design Spec

**Date:** 2026-05-09

## Summary

When viewing shared voice actors for a selected anime, clicking an actor's name opens a persistent side panel showing all anime and roles they have voiced within the user's watchlist.

## User Story

> "I see Enoki, Junya in Jujutsu Kaisen — I want to click his name and immediately see every anime he voiced and which character he played in each."

## Layout

The overlap results area (currently a single-column actor list) becomes a two-column layout:

- **Left column:** actor list (existing cards, slightly narrowed)
- **Right column:** sticky detail panel, visible once an actor is selected

On initial load (no actor selected), the right panel shows a neutral placeholder: _"Select a voice actor to see their roles."_

## Actor List (left column)

- Each actor card is clickable. Selected actor gets a highlighted border (blue ring).
- The existing anime pill badges remain on cards so the list stays scannable without opening the panel.
- Clicking a different actor swaps the panel content.

## Detail Panel (right column)

### Header
- Actor photo: large circle (~64px), falls back to a placeholder avatar if no photo.
- Actor name: prominent heading.
- Subheading: _"N roles in your watchlist"_ (count of distinct anime).

### Role list
One card per anime the actor appeared in (within the user's watchlist):

| Element | Source |
|---|---|
| Character thumbnail | `appears_in[n].character_photo` |
| Anime name | `appears_in[n].name` (blue, prominent) |
| Character name | `"as " + appears_in[n].character_name` |

## Backend Change

`GET /api/user/anime/{mal_id}/overlap` — extend the `appears_in` items to include character data.

**Current shape:**
```ts
appears_in: Array<{ id: number; name: string; mal_id: number | null }>
```

**New shape:**
```ts
appears_in: Array<{
  id: number
  name: string
  mal_id: number | null
  character_name: string
  character_photo: string | null
}>
```

Implementation: in `get_actor_overlap` (`backend/app/services/anime_actors.py`), when building the `appears_in` list (step 9), look up the character record for this actor in each anime and include `name` and `photo` from it.

## Frontend Components

`dashboard.vue` currently has all UI inline. This feature adds enough complexity to warrant extraction:

### New components

- **`components/ActorCard.vue`** — the clickable actor summary card (left column item). Props: `item: OverlapResult`, `selected: boolean`. Emits: `select`.
- **`components/ActorDetailPanel.vue`** — the right-side panel. Props: `actor: OverlapResult | null`. Shows placeholder when `null`.

### `dashboard.vue` changes

- Wrap the overlap section in a two-column flex/grid layout.
- Track `selectedActor: OverlapResult | null` in local state (reset to `null` when a new anime is selected).
- Pass `selectedActor` to `ActorDetailPanel`.

### Updated TypeScript interface

```ts
interface AppearsInEntry {
  id: number
  name: string
  mal_id: number | null
  character_name: string
  character_photo: string | null
}

interface OverlapResult {
  actor: { id: number; name: string; photo: string | null }
  character_in_new_anime: { id: number; name: string; photo: string | null } | null
  appears_in: AppearsInEntry[]
}
```

## Out of Scope

- Linking to MAL pages for actors or anime.
- Showing anime not in the user's watchlist.
- Pagination of role list (watchlists are typically small enough).
- Mobile / responsive layout (not a priority for this tool).
