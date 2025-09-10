from app.db.models import Actor, Character, CharacterActor, TableNames
from app.db.connection import db
from .base import get_soup_from_url
from typing import Generator
import logging

logger = logging.getLogger(__name__)


def extract_actors_data_from_page(soup) -> Generator[dict[str, str], None, None]:
    """Extract character and actor data from MAL characters page."""
    characters = soup.find('div', class_='js-anime-character-container')
    character_rows = characters.find_all('table', recursive=False)

    for row in character_rows:
        pic, char_info, actor_info = row.find('tr').find_all('td', recursive=False)

        character_photo = pic.find('img').get('data-src')
        character_name = char_info.find('div', class_='js-chara-roll-and-name').text.strip().strip('m_')

        all_actors = actor_info.find_all('tr', class_='js-anime-character-va-lang')
        japanese_actor = next(
            (actor for actor in all_actors if 'japanese' in actor.text.lower()),
            None
        )
        if not japanese_actor:
            # TODO: log this
            print(f'Japanese actor not found for {character_name}')
            continue

        actor_name = japanese_actor.find('a').text.strip()
        actor_photo = japanese_actor.find('img').get('data-src')

        yield {
            'character_name': character_name,
            'character_photo': character_photo,
            'actor_name': actor_name,
            'actor_photo': actor_photo,
        }

async def fetch_and_insert_actors_data(session, characters_url: str, anime_id: int):
    """Fetch character and actor data from MAL characters page and insert into Supabase."""
    logger.info(f"👥 Fetching characters from: {characters_url} (anime_id: {anime_id})")
    soup = await get_soup_from_url(session, characters_url)
    if not soup:
        logger.error(f"❌ Failed to get soup from characters URL: {characters_url}")
        return

    character_count = 0
    for actor_data in extract_actors_data_from_page(soup):
        actor_info = {
            'name': actor_data['actor_name'],
            'photo': actor_data['actor_photo'],
        }
        character_info = {
            'name': actor_data['character_name'],
            'photo': actor_data['character_photo'],
            'anime_id': anime_id,
        }
        actor = Actor(**actor_info).save()
        character = Character(**character_info).save()

        character_actor_info = {
            'character_id': character.id,
            'actor_id': actor.id,
        }
        CharacterActor(**character_actor_info).save()
