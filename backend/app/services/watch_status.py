STATUS_ORDER = {
    'completed': 0,
    'watching': 1,
    'plan_to_watch': 2,
    'plan to watch': 2,
}


def watch_status_rank(status: str | None) -> int:
    normalized = (status or '').strip().lower().replace('-', '_')
    return STATUS_ORDER.get(normalized, len(STATUS_ORDER))
