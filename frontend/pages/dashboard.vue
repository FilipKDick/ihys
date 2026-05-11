<script setup lang="ts">
import type { OverlapResult } from '~/composables/useAnimeOverlap'

import { getWatchStatusClass, getWatchStatusLabel } from '~/composables/useWatchStatusStyles'

const { user, checkAuth } = useAuth()
const config = useRuntimeConfig()

const watchHistory = ref<Array<{
  id: number
  anime: { id: number; name: string; mal_id: number | null }
  watch_status: string
}>>([])
const loadingHistory = ref(true)
const syncing = ref(false)

const { results: searchResults, loading: searching, search, clear: clearSearch } = useAnimeSearch()
const searchQuery = ref('')
const showDropdown = computed(() => searchResults.value.length > 0)

const { overlap, loading: loadingOverlap, error: overlapError, fetchOverlap } = useAnimeOverlap()
const selectedAnime = ref<{ mal_id: number; title: string } | null>(null)
const selectedActor = ref<OverlapResult | null>(null)

onMounted(async () => {
  const authenticated = await checkAuth()
  if (!authenticated) {
    await navigateTo('/')
    return
  }
  await loadWatchHistory()
})

async function loadWatchHistory() {
  loadingHistory.value = true
  try {
    watchHistory.value = await $fetch('/api/user/anime', {
      baseURL: config.public.apiBase,
      credentials: 'include',
    })
  } catch {
    watchHistory.value = []
  } finally {
    loadingHistory.value = false
  }
}

async function syncFromMal() {
  syncing.value = true
  try {
    await $fetch('/api/user/anime/sync', {
      method: 'POST',
      baseURL: config.public.apiBase,
      credentials: 'include',
    })
    await loadWatchHistory()
  } finally {
    syncing.value = false
  }
}

function onSearchInput() {
  search(searchQuery.value)
}

type SelectableAnime = {
  mal_id: number
  title: string
  image?: string | null
  year?: string | null
}

async function selectAnime(anime: SelectableAnime) {
  selectedAnime.value = anime
  selectedActor.value = null
  searchQuery.value = anime.title
  clearSearch()
  window.scrollTo({ top: 0, behavior: 'smooth' })
  await fetchOverlap(anime.mal_id)
}

async function selectHistoryAnime(entry: { anime: { name: string; mal_id: number | null } }) {
  if (!entry.anime.mal_id) return

  await selectAnime({
    mal_id: entry.anime.mal_id,
    title: entry.anime.name,
  })
}
</script>

<template>
  <div class="max-w-5xl mx-auto p-4">
    <!-- Header -->
    <div class="flex flex-wrap items-center justify-between gap-3 mb-6">
      <h1 class="text-2xl font-bold">Who's That Seiyuu?</h1>
      <div class="flex flex-wrap items-center justify-end gap-3">
        <span class="text-gray-500 dark:text-gray-400 text-sm">{{ user?.username }}</span>
        <UColorModeSelect size="sm" class="w-32" />
        <UButton size="sm" variant="outline" :loading="syncing" @click="syncFromMal">
          Sync from MAL
        </UButton>
      </div>
    </div>

    <!-- Anime search -->
    <div class="relative">
      <UInput
        v-model="searchQuery"
        placeholder="Search any anime..."
        icon="i-heroicons-magnifying-glass"
        :loading="searching"
        @input="onSearchInput"
      />
      <div
        v-if="showDropdown"
        class="absolute z-10 w-full bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-md shadow-lg mt-1 overflow-hidden"
      >
        <button
          v-for="anime in searchResults"
          :key="anime.mal_id"
          class="w-full text-left px-4 py-2 hover:bg-gray-100 dark:hover:bg-gray-800 flex items-center justify-between text-sm"
          @click="selectAnime(anime)"
        >
          <span>{{ anime.title }}</span>
          <span class="text-gray-500 dark:text-gray-400">{{ anime.year }}</span>
        </button>
      </div>
    </div>

    <!-- Overlap results -->
    <div v-if="selectedAnime" class="mt-8">
      <h2 class="text-lg font-semibold mb-1">{{ selectedAnime.title }}</h2>

      <div v-if="loadingOverlap" class="text-gray-500 dark:text-gray-400 text-sm">
        Fetching actor data... (first lookup may take a few seconds)
      </div>
      <div v-else-if="overlapError" class="text-red-600 dark:text-red-400 text-sm">{{ overlapError }}</div>
      <div v-else-if="overlap.length === 0" class="text-gray-500 dark:text-gray-400 text-sm">
        No shared voice actors found.
      </div>
      <div v-else>
        <p class="text-xs text-gray-500 dark:text-gray-400 uppercase tracking-widest mb-3">
          {{ overlap.length }} shared voice actor{{ overlap.length !== 1 ? 's' : '' }}
        </p>
        <div class="flex flex-col md:flex-row gap-4 items-start">
          <!-- Actor list (+ inline panel on mobile) -->
          <div class="flex flex-col gap-3 w-full md:w-1/2 md:flex-shrink-0">
            <template v-for="item in overlap" :key="item.actor.id">
              <ActorCard
                :item="item"
                :selected="selectedActor?.actor.id === item.actor.id"
                @select="selectedActor = $event"
              />
              <!-- On mobile: panel appears immediately below the selected actor -->
              <div v-if="selectedActor?.actor.id === item.actor.id" class="md:hidden">
                <ActorDetailPanel :actor="selectedActor" />
              </div>
            </template>
          </div>
          <!-- Detail panel: desktop only -->
          <div v-if="selectedActor" class="hidden md:block flex-1 sticky top-4">
            <ActorDetailPanel :actor="selectedActor" />
          </div>
        </div>
      </div>
    </div>

    <!-- Watch history -->
    <div class="mt-6">
      <p class="text-xs text-gray-500 dark:text-gray-400 uppercase tracking-widest mb-3">
        Watch history ({{ watchHistory.length }})
      </p>
      <div v-if="loadingHistory" class="text-gray-500 dark:text-gray-400 text-sm">Loading...</div>
      <div v-else class="flex flex-col gap-1">
        <button
          v-for="entry in watchHistory"
          :key="entry.id"
          :disabled="!entry.anime.mal_id"
          class="flex items-center justify-between bg-white dark:bg-gray-900 border border-gray-200 dark:border-transparent rounded px-3 py-2 text-left text-sm transition hover:bg-gray-50 dark:hover:bg-gray-800 disabled:cursor-not-allowed disabled:opacity-60"
          @click="selectHistoryAnime(entry)"
        >
          <span>{{ entry.anime.name }}</span>
          <span
            class="inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset"
            :class="getWatchStatusClass(entry.watch_status)"
          >
            {{ getWatchStatusLabel(entry.watch_status) }}
          </span>
        </button>
        <div v-if="watchHistory.length === 0" class="text-gray-500 dark:text-gray-400 text-sm">
          No anime yet — sync from MAL to get started.
        </div>
      </div>
    </div>
  </div>
</template>
