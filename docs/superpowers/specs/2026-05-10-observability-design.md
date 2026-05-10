# Observability Design: Sentry + Umami

## Overview

Add error tracking (Sentry cloud) and privacy-friendly analytics (Umami self-hosted) to the Who's That Seiyuu stack. No cookie banner required — Umami is cookieless by design and Sentry operates under legitimate interest for error reporting.

---

## Sentry (Error Tracking)

### Backend

- Add `sentry-sdk[fastapi]` to `pyproject.toml` dependencies.
- Initialize Sentry in `backend/app/main.py` before the `FastAPI()` instance is created.
- Initialization is gated on `settings.SENTRY_DSN` being set — if unset (local dev), Sentry is silently skipped.
- The FastAPI integration (`sentry_sdk.integrations.fastapi.FastApiIntegration`) auto-captures unhandled exceptions with full request context. No changes to route handlers.
- `traces_sample_rate=0.1` (10% of requests get performance traces — enough signal, minimal overhead).

### Frontend

- Add `@sentry/nuxt` to `frontend/package.json`.
- Register via `nuxt.config.ts` modules array with `dsn: process.env.NUXT_PUBLIC_SENTRY_DSN`.
- Only active when `NUXT_PUBLIC_SENTRY_DSN` is set — local dev works without it.
- Captures unhandled JS errors and Vue component errors automatically.

### Configuration

New env vars:

| Var | File | Description |
|---|---|---|
| `SENTRY_DSN` | `.env.backend` | Backend DSN from sentry.io project settings |
| `NUXT_PUBLIC_SENTRY_DSN` | `.env.frontend` | Frontend DSN (can be same project, different DSN) |

Both added as optional to their respective `.dist` files with instructions to get the DSN from sentry.io.

`SENTRY_DSN` added to `config.py` as `sentry_dsn: str | None = None`.

### Setup steps (manual, one-time)

1. Create a free account at sentry.io.
2. Create two projects: one Python/FastAPI, one JavaScript/Nuxt.
3. Copy each DSN into the env files.

---

## Umami (Analytics)

### New Docker services

Two new containers added to `compose.yml`:

**`umami_postgres`** — dedicated Postgres 17 instance for Umami's data. Internal only, not exposed on host. Credentials from new env vars `UMAMI_POSTGRES_USER`, `UMAMI_POSTGRES_PASSWORD`, `UMAMI_POSTGRES_DB`.

**`umami`** — official `ghcr.io/umami-software/umami:postgresql-latest` image. Connects to `umami_postgres`. Listens on internal port 3000. `APP_SECRET` set from `UMAMI_APP_SECRET` env var (used for JWT signing — should be a random string).

Neither container is exposed directly on the host — traffic goes through Caddy.

### Caddy routing

Add a new site block to `Caddyfile` for `analytics.{$DOMAIN}` → `umami:3000`. TLS handled automatically by Caddy/Let's Encrypt, same as the main app.

### Frontend tracking script

A single `<script>` tag added to `app.vue`:

```html
<script
  async
  defer
  src="https://analytics.{domain}/script.js"
  data-website-id="{NUXT_PUBLIC_UMAMI_WEBSITE_ID}"
/>
```

- Only injected when `NUXT_PUBLIC_UMAMI_WEBSITE_ID` is set (empty in local dev = no tracking).
- Uses Nuxt's `useHead` composable in `app.vue` to inject the script conditionally.

### Configuration

New env vars:

| Var | File | Description |
|---|---|---|
| `UMAMI_POSTGRES_USER` | `.env` | Umami DB username |
| `UMAMI_POSTGRES_PASSWORD` | `.env` | Umami DB password |
| `UMAMI_POSTGRES_DB` | `.env` | Umami DB name |
| `UMAMI_APP_SECRET` | `.env` | Random string for JWT signing |
| `NUXT_PUBLIC_UMAMI_WEBSITE_ID` | `.env.frontend` | Site UUID from Umami admin UI |
| `NUXT_PUBLIC_UMAMI_SCRIPT_URL` | `.env.frontend` | Full URL to script.js (e.g. `https://analytics.yourdomain.com/script.js`) |

All added to `.env.dist` and `.env.frontend.dist` with comments.

### Setup steps (manual, one-time)

1. Start the stack — Umami initialises its DB on first run.
2. Visit `analytics.yourdomain.com`, log in with default credentials (`admin` / `umami`).
3. **Immediately change the password.**
4. Add a website in the Umami UI, copy the website UUID into `NUXT_PUBLIC_UMAMI_WEBSITE_ID`.

---

## What is NOT in scope

- Sentry performance tracing dashboards (alerts, custom instrumentation) — default auto-capture is sufficient.
- Umami custom events (beyond page views) — can be added later with `umami.track()`.
- Umami on a subpath of the main domain (subdomain is cleaner and avoids Caddy regex complexity).
