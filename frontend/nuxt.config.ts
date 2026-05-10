// https://nuxt.com/docs/api/configuration/nuxt-config
export default defineNuxtConfig({
  compatibilityDate: '2025-05-15',
  devtools: { enabled: process.env.NODE_ENV !== 'production' },

  modules: [
    '@nuxt/eslint',
    '@nuxt/fonts',
    '@nuxt/icon',
    '@nuxt/image',
    '@nuxt/ui',
    '@sentry/nuxt/module'
  ],
  css: ['~/assets/css/main.css'],
  runtimeConfig: {
    public: {
      apiBase: process.env.NUXT_PUBLIC_API_BASE_URL || '',
      sentryDsn: process.env.NUXT_PUBLIC_SENTRY_DSN || '',
      umamiWebsiteId: process.env.NUXT_PUBLIC_UMAMI_WEBSITE_ID || '',
      umamiScriptUrl: process.env.NUXT_PUBLIC_UMAMI_SCRIPT_URL || '',
    }
  },
  sentry: {
    sourceMapsUploadOptions: {
      org: process.env.SENTRY_ORG || '',
      project: process.env.SENTRY_PROJECT || '',
      authToken: process.env.SENTRY_AUTH_TOKEN || '',
    }
  }
})
