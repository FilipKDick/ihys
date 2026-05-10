<script setup lang="ts">
const { checkAuth } = useAuth()
const config = useRuntimeConfig()

const checking = ref(true)

onMounted(async () => {
  const authenticated = await checkAuth()
  if (authenticated) {
    await navigateTo('/dashboard')
  }
  checking.value = false
})

const loginUrl = `${config.public.apiBase}/api/auth/login`
</script>

<template>
  <div class="flex min-h-screen items-center justify-center bg-gray-950">
    <div v-if="!checking" class="text-center">
      <h1 class="text-4xl font-bold mb-2">IHYS</h1>
      <p class="text-gray-400 mb-8">In how many animes you've seen this actor?</p>
      <UButton :to="loginUrl" external size="lg" color="primary">
        Login with MyAnimeList
      </UButton>
      <p class="mt-6 text-xs text-gray-600">
        By logging in you agree to our
        <NuxtLink to="/privacy" class="underline hover:text-gray-400">Privacy Policy</NuxtLink>.
      </p>
    </div>
  </div>
</template>
