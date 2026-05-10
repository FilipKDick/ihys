import * as Sentry from '@sentry/nuxt'

const config = useRuntimeConfig()

if (config.public.sentryDsn) {
  Sentry.init({
    dsn: config.public.sentryDsn,
    tracesSampleRate: 0.1,
  })
}
