<script setup lang="ts">
import type { OverlapResult } from '~/composables/useAnimeOverlap'

import { getWatchStatusClass, getWatchStatusLabel } from '~/composables/useWatchStatusStyles'

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
        <div v-else class="w-16 h-16 rounded-full bg-gray-700 flex-shrink-0" aria-hidden="true" />
        <div>
          <p class="font-semibold text-lg leading-tight">{{ actor.actor.name }}</p>
          <p v-if="actor.character_in_new_anime" class="text-sm text-gray-300">
            as {{ actor.character_in_new_anime.name }} in this anime
          </p>
          <p class="text-sm text-gray-400">
            {{ actor.appears_in.length }} role{{ actor.appears_in.length !== 1 ? 's' : '' }} in your watchlist
          </p>
        </div>
      </div>

      <!-- Role list -->
      <div class="flex flex-col gap-3 overflow-y-auto max-h-[calc(100vh-12rem)]">
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
          <div v-else class="w-10 h-10 rounded bg-gray-700 flex-shrink-0" aria-hidden="true" />
          <div class="min-w-0 flex-1">
            <div class="flex items-start justify-between gap-2">
              <p class="text-blue-300 font-medium text-sm">{{ entry.name }}</p>
              <span
                class="inline-flex flex-shrink-0 items-center rounded-full px-2 py-0.5 text-[11px] font-medium ring-1 ring-inset"
                :class="getWatchStatusClass(entry.watch_status)"
              >
                {{ getWatchStatusLabel(entry.watch_status) }}
              </span>
            </div>
            <p class="text-gray-400 text-xs">as {{ entry.character_name }}</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
