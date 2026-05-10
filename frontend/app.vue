<template>
  <NuxtRouteAnnouncer />
  <NuxtPage />
</template>

<script setup lang="ts">
const config = useRuntimeConfig()

if (config.public.umamiWebsiteId && config.public.umamiScriptUrl) {
  useHead({
    script: [
      {
        src: config.public.umamiScriptUrl,
        defer: true,
        'data-website-id': config.public.umamiWebsiteId,
      },
    ],
  })
}
</script>
