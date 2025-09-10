from app.db.models import Actor, Character, CharacterActor

from app.db.base import AsyncSessionLocal
from sqlmodel import select

from .base import get_soup_from_url


def extract_actors_data_from_page(soup):
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


async def fetch_and_insert_actors_data(session, characters_url, anime_id):
    soup = await get_soup_from_url(session, characters_url)
    if not soup:
        return
    async with AsyncSessionLocal() as db:
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

            # Check if actor exists
            result = await db.execute(select(Actor).where(Actor.name == actor_info['name']))
            existing_actor = result.scalar_one_or_none()

            if not existing_actor:
                actor = Actor.model_validate(actor_info)
                db.add(actor)
                await db.commit()
                await db.refresh(actor)
            else:
                actor = existing_actor

            character = Character.model_validate(character_info)
            db.add(character)
            await db.commit()
            await db.refresh(character)

            character_actor = CharacterActor(character_id=character.id, actor_id=actor.id)
            db.add(character_actor)
            await db.commit()