from bs4 import BeautifulSoup
from .base import get_soup_from_url
from app.db.base import AsyncSessionLocal
from app.db.models import Anime


def parse_mal_anime_page(soup: BeautifulSoup) -> dict:
    result = {}

    # Extract English title
    english_title_elem = soup.find('span', class_='dark_text', string='English:')
    if english_title_elem and english_title_elem.parent:
        english_title = english_title_elem.parent.get_text().replace('English:', '').strip()
        result['english_title'] = english_title

    # Extract Japanese title
    japanese_title_elem = soup.find('span', class_='dark_text', string='Japanese:')
    if japanese_title_elem and japanese_title_elem.parent:
        japanese_title = japanese_title_elem.parent.get_text().replace('Japanese:', '').strip()
        result['japanese_title'] = japanese_title

    # Find all information fields
    info_elements = soup.find_all('div', class_='spaceit_pad')
    for elem in info_elements:
        dark_text = elem.find('span', class_='dark_text')
        if dark_text:
            key = dark_text.get_text().replace(':', '').strip().lower()
            value = elem.get_text().replace(dark_text.get_text(), '').strip()

            value = ' '.join(value.split())

            if key and value:
                result[key] = value

    # Extract Synopsis
    synopsis_elem = soup.find('p', {'itemprop': 'description'})
    if synopsis_elem:
        synopsis = synopsis_elem.get_text().strip()
        synopsis = synopsis.replace('[Written by MAL Rewrite]', '').strip()
        result['synopsis'] = synopsis
    result['name'] = result.get('english_title') or result.get('japanese_title') or 'Unknown'
    return result


async def fetch_and_insert_anime_data(session, url: str) -> Anime | None:
    soup = await get_soup_from_url(session, url)
    if not soup:
        return None
    scraped_data = parse_mal_anime_page(soup)
    async with AsyncSessionLocal() as db:
        new_anime = Anime.model_validate(scraped_data)
        db.add(new_anime)
        await db.commit()
        await db.refresh(new_anime)
        return new_anime
