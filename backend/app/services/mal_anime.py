from app.db.connection import db
from app.db.models import Anime
from app.schemas.mal import MalAnimeNode


class MALApiError(Exception):
    pass


def ensure_anime_record(anime: MalAnimeNode) -> Anime:
    if existing_anime := db.get_records('anime', {'mal_id': anime.id}):
        record = existing_anime[0]
        if anime.status and record.get('status') != anime.status:
            db.update_record('anime', record['id'], {'status': anime.status})
            record['status'] = anime.status
        return Anime.model_validate(record)

    created = db.insert_record('anime', anime.to_anime_insert_data())
    if not created:
        raise MALApiError(f'Failed to create anime record for MAL id {anime.id}')
    return Anime.model_validate(created)
