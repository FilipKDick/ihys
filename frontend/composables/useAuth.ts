export interface AuthUser {
  id: number
  username: string
}

export const useAuth = () => {
  const config = useRuntimeConfig()
  const user = useState<AuthUser | null>('auth-user', () => null)

  const checkAuth = async (): Promise<boolean> => {
    try {
      const data = await $fetch<AuthUser>('/api/auth/me', {
        baseURL: config.public.apiBase,
        credentials: 'include',
      })
      user.value = data
      return true
    } catch {
      user.value = null
      return false
    }
  }

  return { user, checkAuth }
}
