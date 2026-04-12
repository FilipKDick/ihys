export interface AnimeSearchResult {
  mal_id: number
  title: string
  image: string | null
  year: string | null
}

export const useAnimeSearch = () => {
  const config = useRuntimeConfig()
  const results = ref<AnimeSearchResult[]>([])
  const loading = ref(false)
  let timer: ReturnType<typeof setTimeout> | null = null

  const search = (query: string) => {
    if (timer) clearTimeout(timer)
    if (!query || query.length < 2) {
      results.value = []
      return
    }
    timer = setTimeout(async () => {
      loading.value = true
      try {
        results.value = await $fetch<AnimeSearchResult[]>('/api/anime/search', {
          baseURL: config.public.apiBase,
          credentials: 'include',
          params: { q: query },
        })
      } catch {
        results.value = []
      } finally {
        loading.value = false
      }
    }, 300)
  }

  const clear = () => {
    if (timer) clearTimeout(timer)
    results.value = []
  }

  return { results, loading, search, clear }
}
