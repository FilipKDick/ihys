const STATUS_STYLES: Record<string, { label: string; class: string }> = {
  completed: {
    label: 'Completed',
    class: 'bg-emerald-950 text-emerald-300 ring-emerald-800',
  },
  watching: {
    label: 'Watching',
    class: 'bg-sky-950 text-sky-300 ring-sky-800',
  },
  plan_to_watch: {
    label: 'Plan to watch',
    class: 'bg-amber-950 text-amber-300 ring-amber-800',
  },
  'plan to watch': {
    label: 'Plan to watch',
    class: 'bg-amber-950 text-amber-300 ring-amber-800',
  },
}

const DEFAULT_STATUS_STYLE = {
  label: 'Other',
  class: 'bg-gray-800 text-gray-300 ring-gray-700',
}

function normalizeWatchStatus(status: string) {
  return status.trim().toLowerCase().replaceAll('-', '_')
}

export function getWatchStatusLabel(status: string) {
  const normalized = normalizeWatchStatus(status)
  const style = STATUS_STYLES[normalized]

  if (style) return style.label
  if (!normalized) return DEFAULT_STATUS_STYLE.label

  return normalized
    .replaceAll('_', ' ')
    .replace(/\b\w/g, (letter) => letter.toUpperCase())
}

export function getWatchStatusClass(status: string) {
  const normalized = normalizeWatchStatus(status)
  return STATUS_STYLES[normalized]?.class ?? DEFAULT_STATUS_STYLE.class
}
