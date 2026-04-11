import aiohttp
import logging

from app.db.connection import db
from scrapers.characters import fetch_and_insert_actors_data

logger = logging.getLogger(__name__)


async def ensure_actor_data(anime_id: int, mal_id: int) -> None:
    """Scrape and store actor/character data for an anime if not already in DB."""
    existing = db.get_records('characters', {'anime_id': anime_id})
    if existing:
        return

    characters_url = f'https://myanimelist.net/anime/{mal_id}/characters'
    logger.info(f'Scraping actors for anime_id={anime_id} mal_id={mal_id}')
    async with aiohttp.ClientSession() as session:
        await fetch_and_insert_actors_data(session, characters_url, anime_id)


def get_actor_overlap(mal_id: int, user_id: int) -> list[dict]:
    """
    Return actors who appear in the given anime AND in the user's watch history.

    Each result item:
      {
        'actor': {'id', 'name', 'photo'},
        'character_in_new_anime': {'id', 'name', 'photo'} | None,
        'appears_in': [{'id', 'name', 'mal_id'}, ...],
      }
    """
    # 1. Find the anime by MAL ID
    animes = db.get_records('anime', {'mal_id': mal_id})
    if not animes:
        return []
    anime_db_id = animes[0]['id']

    # 2. Characters in the searched anime
    chars_in_anime = db.get_records('characters', {'anime_id': anime_db_id})
    if not chars_in_anime:
        return []
    char_ids_in_anime = [c['id'] for c in chars_in_anime]

    # 3. Actors for those characters
    ca_in_anime = db.get_records_by_ids('character_actors', 'character_id', char_ids_in_anime)
    actor_ids_in_anime = {ca['actor_id'] for ca in ca_in_anime}

    # 4. User's watch history
    user_anime_records = db.get_records('user_anime', {'user_id': user_id})
    if not user_anime_records:
        return []
    user_anime_ids = [ua['anime_id'] for ua in user_anime_records]

    # 5. Characters in watched anime
    chars_in_history = db.get_records_by_ids('characters', 'anime_id', user_anime_ids)
    if not chars_in_history:
        return []
    char_ids_in_history = [c['id'] for c in chars_in_history]

    # 6. Actors in watched anime
    ca_in_history = db.get_records_by_ids('character_actors', 'character_id', char_ids_in_history)
    actor_ids_in_history = {ca['actor_id'] for ca in ca_in_history}

    # 7. Intersection
    shared_actor_ids = actor_ids_in_anime & actor_ids_in_history
    if not shared_actor_ids:
        return []

    # 8. Build lookup maps
    char_map = {c['id']: c for c in chars_in_anime}
    history_char_map = {c['id']: c for c in chars_in_history}

    actor_to_new_char: dict[int, dict | None] = {}
    for ca in ca_in_anime:
        if ca['actor_id'] in shared_actor_ids and ca['actor_id'] not in actor_to_new_char:
            actor_to_new_char[ca['actor_id']] = char_map.get(ca['character_id'])

    actor_to_history_char_ids: dict[int, list[int]] = {}
    for ca in ca_in_history:
        if ca['actor_id'] in shared_actor_ids:
            actor_to_history_char_ids.setdefault(ca['actor_id'], []).append(ca['character_id'])

    # 9. Build results
    anime_cache: dict[int, dict] = {}
    result = []

    for actor_id in shared_actor_ids:
        actor = db.get_record_by_id('actors', actor_id)
        if not actor:
            continue

        char_in_new = actor_to_new_char.get(actor_id)

        seen_anime_ids: set[int] = set()
        appears_in = []
        for char_id in actor_to_history_char_ids.get(actor_id, []):
            char = history_char_map.get(char_id)
            if not char:
                continue
            aid = char['anime_id']
            if aid in seen_anime_ids:
                continue
            seen_anime_ids.add(aid)
            if aid not in anime_cache:
                anime_cache[aid] = db.get_record_by_id('anime', aid) or {}
            a = anime_cache[aid]
            if a:
                appears_in.append({'id': a['id'], 'name': a['name'], 'mal_id': a.get('mal_id')})

        result.append({
            'actor': {'id': actor['id'], 'name': actor['name'], 'photo': actor['photo']},
            'character_in_new_anime': {
                'id': char_in_new['id'],
                'name': char_in_new['name'],
                'photo': char_in_new.get('photo'),
            } if char_in_new else None,
            'appears_in': appears_in,
        })

    return result
