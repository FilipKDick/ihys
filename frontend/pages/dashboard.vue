<script setup lang="ts">
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

async function selectAnime(anime: { mal_id: number; title: string; image: string | null; year: string | null }) {
  selectedAnime.value = anime
  searchQuery.value = anime.title
  clearSearch()
  await fetchOverlap(anime.mal_id)
}
</script>

<template>
  <div class="max-w-2xl mx-auto p-4">
    <!-- Header -->
    <div class="flex items-center justify-between mb-6">
      <h1 class="text-2xl font-bold">IHYS</h1>
      <div class="flex items-center gap-3">
        <span class="text-gray-400 text-sm">{{ user?.username }}</span>
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
        class="absolute z-10 w-full bg-gray-900 border border-gray-700 rounded-md shadow-lg mt-1 overflow-hidden"
      >
        <button
          v-for="anime in searchResults"
          :key="anime.mal_id"
          class="w-full text-left px-4 py-2 hover:bg-gray-800 flex items-center justify-between text-sm"
          @click="selectAnime(anime)"
        >
          <span>{{ anime.title }}</span>
          <span class="text-gray-500">{{ anime.year }}</span>
        </button>
      </div>
    </div>

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
        <div class="flex flex-col gap-3">
          <div
            v-for="item in overlap"
            :key="item.actor.id"
            class="bg-gray-900 rounded-lg p-3 flex items-start gap-3"
          >
            <img
              v-if="item.actor.photo"
              :src="item.actor.photo"
              :alt="item.actor.name"
              class="w-10 h-10 rounded-full object-cover flex-shrink-0"
            />
            <div class="flex-1">
              <p class="font-medium">{{ item.actor.name }}</p>
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
          </div>
        </div>
      </div>
    </div>

    <!-- Watch history -->
    <div class="mt-6">
      <p class="text-xs text-gray-500 uppercase tracking-widest mb-3">
        Watch history ({{ watchHistory.length }})
      </p>
      <div v-if="loadingHistory" class="text-gray-400 text-sm">Loading...</div>
      <div v-else class="flex flex-col gap-1">
        <div
          v-for="entry in watchHistory"
          :key="entry.id"
          class="flex items-center justify-between bg-gray-900 rounded px-3 py-2 text-sm"
        >
          <span>{{ entry.anime.name }}</span>
          <span class="text-gray-500 capitalize">{{ entry.watch_status }}</span>
        </div>
        <div v-if="watchHistory.length === 0" class="text-gray-500 text-sm">
          No anime yet — sync from MAL to get started.
        </div>
      </div>
    </div>
  </div>
</template>
