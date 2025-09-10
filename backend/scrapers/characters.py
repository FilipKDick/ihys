from app.db.models import Actor, Character, TableNames
from app.db.base import db
from .base import get_soup_from_url
from typing import Generator


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
    soup = await get_soup_from_url(session, characters_url)
    if not soup:
        return

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

        # Insert or get existing actor using upsert
        actor_result = db.upsert_record(
            table_name=TableNames.ACTORS,
            data=actor_info,
            conflict_columns=['name']
        )

        if not actor_result:
            print(f"Failed to insert actor: {actor_info['name']}")
            continue

        actor = Actor(**actor_result)

        character_result = db.upsert_record(
            table_name=TableNames.CHARACTERS,
            data=character_info,
            conflict_columns=['name', 'anime_id']
        )

        if not character_result:
            print(f"Failed to insert character: {character_info['name']}")
            continue

        character = Character(**character_result)

        # Create character-actor relationship
        character_actor_info = {
            'character_id': character.id,
            'actor_id': actor.id,
        }

        db.upsert_record(
            table_name=TableNames.CHARACTER_ACTORS,
            data=character_actor_info,
            conflict_columns=['character_id', 'actor_id']
        )
