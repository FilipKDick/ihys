from typing import Any

from app.db.connection import db
from app.schemas.mal import MalAnimeNode


class MALApiError(Exception):
    pass


def ensure_anime_record(anime: MalAnimeNode) -> dict[str, Any]:
    existing_anime = db.get_records('anime', {'mal_id': anime.id})
    if existing_anime:
        record = existing_anime[0]
        if anime.status and record.get('status') != anime.status:
            db.update_record('anime', record['id'], {'status': anime.status})
            record['status'] = anime.status
        return record

    name_match = db.get_records('anime', {'name': anime.title})
    if name_match:
        record = name_match[0]
        update_data: dict[str, str | int] = {'mal_id': anime.id}
        if anime.status:
            update_data['status'] = anime.status
            record['status'] = anime.status
        db.update_record('anime', record['id'], update_data)
        record['mal_id'] = anime.id
        return record

    created = db.insert_record('anime', anime.to_anime_insert_data())
    if not created:
        raise MALApiError(
            f'Failed to create anime record for MAL id {anime.id}',
        )
    return created
