STATUS_ORDER = {
    'completed': 0,
    'watching': 1,
    'plan_to_watch': 2,
    'plan to watch': 2,
}

COUNTED_OVERLAP_STATUSES = {'completed', 'watching'}


def normalize_watch_status(status: str | None) -> str:
    return (status or '').strip().lower().replace('-', '_')


def watch_status_rank(status: str | None) -> int:
    normalized = normalize_watch_status(status)
    return STATUS_ORDER.get(normalized, len(STATUS_ORDER))


def counts_for_actor_overlap_order(status: str | None) -> bool:
    return normalize_watch_status(status) in COUNTED_OVERLAP_STATUSES
