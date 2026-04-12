export interface OverlapResult {
  actor: { id: number; name: string; photo: string | null }
  character_in_new_anime: { id: number; name: string; photo: string | null } | null
  appears_in: Array<{ id: number; name: string; mal_id: number | null }>
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
