# Actor Detail Panel Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Clicking a voice actor in the overlap list opens a side panel showing their photo, name, and every anime+character role they've voiced in the user's watchlist.

**Architecture:** Backend extends `appears_in` items to include `character_name` and `character_photo`. Frontend splits the overlap area into two columns — actor list (left) and a sticky detail panel (right) — using two new extracted components. `selectedActor` state in `dashboard.vue` drives the panel.

**Tech Stack:** FastAPI (Python), Nuxt 3 + Vue 3 Composition API, TypeScript, Tailwind via @nuxt/ui, `@nuxt/image` for photos.

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `backend/app/services/anime_actors.py` | Modify | Add `character_name`/`character_photo` to `appears_in` items in `get_actor_overlap` |
| `frontend/composables/useAnimeOverlap.ts` | Modify | Extend `AppearsInEntry` type with `character_name` and `character_photo` |
| `frontend/components/ActorCard.vue` | Create | Clickable actor summary card (left column) |
| `frontend/components/ActorDetailPanel.vue` | Create | Right-side detail panel showing full role list |
| `frontend/pages/dashboard.vue` | Modify | Two-column layout, `selectedActor` state, wire up components |

---

### Task 1: Extend backend `appears_in` with character data

**Files:**
- Modify: `backend/app/services/anime_actors.py`

The `get_actor_overlap` function builds `appears_in` in a loop starting at line 169. Currently it only appends `{ id, name, mal_id }` from the anime record. We need to also find the character this actor voiced in that anime.

The data is already in memory: `actor_to_history_char_ids` maps `actor_id → [character_id, ...]` and `history_char_map` maps `character_id → character_record`. We just need to pick the first character in that anime for this actor.

- [ ] **Step 1: Update the `appears_in` building loop**

In `backend/app/services/anime_actors.py`, replace the loop at lines 169–181:

```python
        for char_id in actor_to_history_char_ids.get(actor_id, []):
            char = history_char_map.get(char_id)
            if not char:
                continue
            aid = char['anime_id']
            if aid in seen_anime_ids:
                continue
            seen_anime_ids.add(aid)
            a = anime_cache.get(aid, {})
            if a:
                appears_in.append(
                    {'id': a['id'], 'name': a['name'], 'mal_id': a.get('mal_id')},
                )
```

Replace with:

```python
        for char_id in actor_to_history_char_ids.get(actor_id, []):
            char = history_char_map.get(char_id)
            if not char:
                continue
            aid = char['anime_id']
            if aid in seen_anime_ids:
                continue
            seen_anime_ids.add(aid)
            a = anime_cache.get(aid, {})
            if a:
                appears_in.append({
                    'id': a['id'],
                    'name': a['name'],
                    'mal_id': a.get('mal_id'),
                    'character_name': char['name'],
                    'character_photo': char.get('photo') or None,
                })
```

- [ ] **Step 2: Run linter**

```bash
docker-compose exec backend ruff check app/services/anime_actors.py
```

Expected: `All checks passed!`

- [ ] **Step 3: Verify response shape manually**

```bash
# Hit the overlap endpoint (replace MAL_ID and adjust cookie as needed)
curl -s -b "your_session_cookie" \
  http://localhost:8002/api/user/anime/40748/overlap \
  | python3 -m json.tool | grep -A5 '"appears_in"'
```

Expected: each `appears_in` item has `character_name` (string) and `character_photo` (string or null).

- [ ] **Step 4: Commit**

```bash
cd backend
git add app/services/anime_actors.py
git commit -m "feat: include character name and photo in overlap appears_in"
```

---

### Task 2: Update TypeScript types in composable

**Files:**
- Modify: `frontend/composables/useAnimeOverlap.ts`

- [ ] **Step 1: Extend `AppearsInEntry` and `OverlapResult`**

Replace the entire file content:

```ts
export interface AppearsInEntry {
  id: number
  name: string
  mal_id: number | null
  character_name: string
  character_photo: string | null
}

export interface OverlapResult {
  actor: { id: number; name: string; photo: string | null }
  character_in_new_anime: { id: number; name: string; photo: string | null } | null
  appears_in: AppearsInEntry[]
}

export const useAnimeOverlap = () => {
  const config = useRuntimeConfig()
  const overlap = ref<OverlapResult[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  const fetchOverlap = async (malId: number) => {
    loading.value = true
    error.value = null
    try {
      overlap.value = await $fetch<OverlapResult[]>(`/api/user/anime/${malId}/overlap`, {
        baseURL: config.public.apiBase,
        credentials: 'include',
      })
    } catch (e: unknown) {
      const err = e as { data?: { detail?: string } }
      error.value = err?.data?.detail ?? 'Could not fetch actor data, try again'
      overlap.value = []
    } finally {
      loading.value = false
    }
  }

  return { overlap, loading, error, fetchOverlap }
}
```

- [ ] **Step 2: Run TypeScript check**

```bash
cd frontend && npm run build 2>&1 | grep -E "error|Error" | head -20
```

Expected: no type errors related to `AppearsInEntry` or `OverlapResult`.

- [ ] **Step 3: Commit**

```bash
git add frontend/composables/useAnimeOverlap.ts
git commit -m "feat: extend OverlapResult type with character_name and character_photo"
```

---

### Task 3: Create `ActorCard.vue` component

**Files:**
- Create: `frontend/components/ActorCard.vue`

This is the left-column card. It shows actor photo, name, character in the new anime, and anime pill badges — same content as the current inline cards in `dashboard.vue`, but now clickable and highlights when selected.

- [ ] **Step 1: Create the component**

```vue
<!-- frontend/components/ActorCard.vue -->
<script setup lang="ts">
import type { OverlapResult } from '~/composables/useAnimeOverlap'

const props = defineProps<{
  item: OverlapResult
  selected: boolean
}>()

const emit = defineEmits<{
  select: [item: OverlapResult]
}>()
</script>

<template>
  <button
    class="w-full text-left bg-gray-900 rounded-lg p-3 flex items-start gap-3 transition-all"
    :class="selected ? 'ring-2 ring-blue-500' : 'hover:bg-gray-800'"
    @click="emit('select', item)"
  >
    <img
      v-if="item.actor.photo"
      :src="item.actor.photo"
      :alt="item.actor.name"
      class="w-10 h-10 rounded-full object-cover flex-shrink-0"
    />
    <div v-else class="w-10 h-10 rounded-full bg-gray-700 flex-shrink-0" />
    <div class="flex-1 min-w-0">
      <p class="font-medium truncate">{{ item.actor.name }}</p>
      <p v-if="item.character_in_new_anime" class="text-sm text-gray-400 mb-2">
        as {{ item.character_in_new_anime.name }}
      </p>
      <div class="flex flex-wrap gap-2">
        <span
          v-for="a in item.appears_in"
          :key="a.id"
          class="bg-gray-800 text-blue-300 text-xs px-2 py-1 rounded-full"
        >
          {{ a.name }}
        </span>
      </div>
    </div>
  </button>
</template>
```

- [ ] **Step 2: Verify no lint errors**

```bash
cd frontend && npm run lint 2>&1 | head -30
```

Expected: no errors in `components/ActorCard.vue`.

- [ ] **Step 3: Commit**

```bash
git add frontend/components/ActorCard.vue
git commit -m "feat: add ActorCard component"
```

---

### Task 4: Create `ActorDetailPanel.vue` component

**Files:**
- Create: `frontend/components/ActorDetailPanel.vue`

This is the right-column panel. When `actor` prop is `null` it shows a placeholder. When set it shows: large actor photo, name, role count, then a card per `appears_in` entry with character thumbnail + anime name + character name.

- [ ] **Step 1: Create the component**

```vue
<!-- frontend/components/ActorDetailPanel.vue -->
<script setup lang="ts">
import type { OverlapResult } from '~/composables/useAnimeOverlap'

defineProps<{
  actor: OverlapResult | null
}>()
</script>

<template>
  <div class="bg-gray-900 rounded-lg p-4 h-full">
    <!-- Placeholder -->
    <div
      v-if="!actor"
      class="flex items-center justify-center h-full min-h-48 text-gray-500 text-sm"
    >
      Select a voice actor to see their roles.
    </div>

    <!-- Actor detail -->
    <div v-else>
      <!-- Header -->
      <div class="flex items-center gap-4 mb-4">
        <img
          v-if="actor.actor.photo"
          :src="actor.actor.photo"
          :alt="actor.actor.name"
          class="w-16 h-16 rounded-full object-cover flex-shrink-0"
        />
        <div v-else class="w-16 h-16 rounded-full bg-gray-700 flex-shrink-0" />
        <div>
          <p class="font-semibold text-lg leading-tight">{{ actor.actor.name }}</p>
          <p class="text-sm text-gray-400">
            {{ actor.appears_in.length }} role{{ actor.appears_in.length !== 1 ? 's' : '' }} in your watchlist
          </p>
        </div>
      </div>

      <!-- Role list -->
      <div class="flex flex-col gap-3">
        <div
          v-for="entry in actor.appears_in"
          :key="entry.id"
          class="bg-gray-800 rounded-lg p-3 flex items-center gap-3"
        >
          <img
            v-if="entry.character_photo"
            :src="entry.character_photo"
            :alt="entry.character_name"
            class="w-10 h-10 rounded object-cover flex-shrink-0"
          />
          <div v-else class="w-10 h-10 rounded bg-gray-700 flex-shrink-0" />
          <div>
            <p class="text-blue-300 font-medium text-sm">{{ entry.name }}</p>
            <p class="text-gray-400 text-xs">as {{ entry.character_name }}</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
```

- [ ] **Step 2: Verify no lint errors**

```bash
cd frontend && npm run lint 2>&1 | head -30
```

Expected: no errors in `components/ActorDetailPanel.vue`.

- [ ] **Step 3: Commit**

```bash
git add frontend/components/ActorDetailPanel.vue
git commit -m "feat: add ActorDetailPanel component"
```

---

### Task 5: Wire up dashboard with two-column layout

**Files:**
- Modify: `frontend/pages/dashboard.vue`

Replace the single-column overlap results section with a two-column layout using the new components. Add `selectedActor` state that resets when a new anime is chosen.

- [ ] **Step 1: Add `selectedActor` state and reset logic**

In the `<script setup>` block, after the `selectedAnime` ref (line 18), add:

```ts
const selectedActor = ref<import('~/composables/useAnimeOverlap').OverlapResult | null>(null)
```

In the `selectAnime` function, reset `selectedActor` when a new anime is selected. Replace:

```ts
async function selectAnime(anime: SelectableAnime) {
  selectedAnime.value = anime
  searchQuery.value = anime.title
  clearSearch()
  await fetchOverlap(anime.mal_id)
}
```

With:

```ts
async function selectAnime(anime: SelectableAnime) {
  selectedAnime.value = anime
  selectedActor.value = null
  searchQuery.value = anime.title
  clearSearch()
  await fetchOverlap(anime.mal_id)
}
```

- [ ] **Step 2: Replace the overlap results template section**

Replace the entire `<!-- Overlap results -->` block (lines 123–168):

```html
<!-- Overlap results -->
<div v-if="selectedAnime" class="mt-8">
  <h2 class="text-lg font-semibold mb-1">{{ selectedAnime.title }}</h2>

  <div v-if="loadingOverlap" class="text-gray-400 text-sm">
    Fetching actor data... (first lookup may take a few seconds)
  </div>
  <div v-else-if="overlapError" class="text-red-400 text-sm">{{ overlapError }}</div>
  <div v-else-if="overlap.length === 0" class="text-gray-500 text-sm">
    No shared voice actors found.
  </div>
  <div v-else>
    <p class="text-xs text-gray-500 uppercase tracking-widest mb-3">
      {{ overlap.length }} shared voice actor{{ overlap.length !== 1 ? 's' : '' }}
    </p>
    <div class="flex gap-4 items-start">
      <!-- Left: actor list -->
      <div class="flex flex-col gap-3 w-1/2 flex-shrink-0">
        <ActorCard
          v-for="item in overlap"
          :key="item.actor.id"
          :item="item"
          :selected="selectedActor?.actor.id === item.actor.id"
          @select="selectedActor = $event"
        />
      </div>
      <!-- Right: detail panel -->
      <div class="flex-1 sticky top-4">
        <ActorDetailPanel :actor="selectedActor" />
      </div>
    </div>
  </div>
</div>
```

- [ ] **Step 3: Widen the page container**

The page is currently constrained to `max-w-2xl`. With two columns this is too narrow. Change the outer div:

```html
<div class="max-w-5xl mx-auto p-4">
```

- [ ] **Step 4: Run lint**

```bash
cd frontend && npm run lint 2>&1 | head -30
```

Expected: no errors.

- [ ] **Step 5: Smoke-test in browser**

1. Open http://localhost:3000
2. Select an anime from watch history or search
3. Verify two-column layout appears: actor list on left, placeholder panel on right
4. Click an actor card — verify panel updates with large photo, name, role count, and role cards with character thumbnails and names
5. Click a different actor — verify panel swaps
6. Select a different anime — verify panel resets to placeholder

- [ ] **Step 6: Commit**

```bash
git add frontend/pages/dashboard.vue
git commit -m "feat: wire up actor detail side panel in dashboard"
```
