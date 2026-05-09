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
    type="button"
    class="w-full text-left bg-gray-900 rounded-lg p-3 flex items-start gap-3 transition-all"
    :class="selected ? 'ring-2 ring-blue-500' : 'hover:bg-gray-800'"
    :aria-pressed="selected"
    @click="emit('select', item)"
  >
    <img
      v-if="item.actor.photo"
      :src="item.actor.photo"
      :alt="item.actor.name"
      class="w-10 h-10 rounded-full object-cover flex-shrink-0"
    />
    <div v-else aria-hidden="true" class="w-10 h-10 rounded-full bg-gray-700 flex-shrink-0" />
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
