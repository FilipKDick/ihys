import logging

from typing import Generator

from app.db.models import Actor, Character, CharacterActor

from .base import get_soup_from_url

logger = logging.getLogger(__name__)


def _image_src(element) -> str:
    image = element.find('img') if element else None
    if not image:
        return ''
    return image.get('data-src') or image.get('src') or ''


def _extract_from_legacy_layout(soup) -> Generator[dict[str, str], None, None]:
    characters = soup.find('div', class_='js-anime-character-container')
    if not characters:
        return

    character_rows = characters.find_all('table', recursive=False)

    for row in character_rows:
        cells = row.find('tr').find_all('td', recursive=False)
        if len(cells) < 3:
            continue
        pic, char_info, actor_info = cells[:3]

        character_name_element = char_info.find(
            'div',
            class_='js-chara-roll-and-name',
        )
        if not character_name_element:
            continue

        character_photo = _image_src(pic)
        character_name = character_name_element.text.strip().strip('m_')

        all_actors = actor_info.find_all('tr', class_='js-anime-character-va-lang')
        japanese_actor = next(
            (actor for actor in all_actors if 'japanese' in actor.text.lower()),
            None,
        )
        if not japanese_actor:
            logger.error(f'Japanese actor not found for {character_name}')
            continue

        actor_link = japanese_actor.find(
            'a',
            href=lambda href: href and '/people/' in href,
        )
        if not actor_link:
            continue

        yield {
            'character_name': character_name,
            'character_photo': character_photo,
            'actor_name': actor_link.text.strip(),
            'actor_photo': _image_src(japanese_actor),
        }


def _extract_from_table_layout(soup) -> Generator[dict[str, str], None, None]:
    character_headings = soup.find_all('h3', class_='h3_characters_voice_actors')

    for heading in character_headings:
        character_link = heading.find(
            'a',
            href=lambda href: href and '/character/' in href,
        )
        character_table = heading.find_parent('table')
        if not character_link or not character_table:
            continue

        cells = character_table.find('tr').find_all('td', recursive=False)
        if len(cells) < 3:
            continue

        character_photo = _image_src(cells[0])
        character_name = character_link.text.strip()
        actor_cell = cells[2]
        japanese_marker = next(
            (
                marker
                for marker in actor_cell.find_all('small')
                if marker.text.strip().lower() == 'japanese'
            ),
            None,
        )
        if not japanese_marker:
            logger.error(f'Japanese actor not found for {character_name}')
            continue

        actor_row = japanese_marker.find_parent('tr')
        actor_link = actor_row.find(
            'a',
            href=lambda href: href and '/people/' in href,
        ) if actor_row else None
        if not actor_link:
            continue

        yield {
            'character_name': character_name,
            'character_photo': character_photo,
            'actor_name': actor_link.text.strip(),
            'actor_photo': _image_src(actor_row),
        }


def extract_actors_data_from_page(soup) -> Generator[dict[str, str], None, None]:
    """Extract character and actor data from MAL characters page."""
    yield from _extract_from_legacy_layout(soup)
    yield from _extract_from_table_layout(soup)


async def fetch_and_insert_actors_data(session, characters_url: str, anime_id: int):
    """Fetch character and actor data from MAL and insert into the database."""
    logger.info(f'👥 Fetching characters from: {characters_url} (anime_id: {anime_id})')
    soup = await get_soup_from_url(session, characters_url)
    if not soup:
        logger.error(f'❌ Failed to get soup from characters URL: {characters_url}')
        return

    count = 0
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
        count += 1

    logger.info(f'✅ Upserted {count} characters for anime_id={anime_id}')
