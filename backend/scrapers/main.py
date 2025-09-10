import time
import logging
from urllib.parse import urljoin
import asyncio
import aiohttp

from .base import get_soup_from_url
from .animes import fetch_and_insert_anime_data
from .characters import fetch_and_insert_actors_data


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# TODO: move to settings
ANIME_PER_PAGE = 50
ANIME_TO_SCRAPE = 1000  # TODO: dict per "top type"
MAX_CONCURRENT = 3
REQUESTS_DELAY = 2.0


class MALScraper:
    def __init__(self, session):
        self.semaphore = asyncio.Semaphore(MAX_CONCURRENT)
        self.last_request_time = 0
        self.lock = asyncio.Lock()
        self.session = session

    async def ensure_delay(self):
        async with self.lock:
            now = time.time()

            if now - self.last_request_time < REQUESTS_DELAY:
                wait_time = REQUESTS_DELAY - (now - self.last_request_time)
                await asyncio.sleep(wait_time)

            self.last_request_time = time.time()

    async def run(self, page_start):
        async with self.semaphore:
            await self.ensure_delay()
            top_anime_list = await self.scrape_top_anime_list(page_start=page_start)

            for anime in top_anime_list:
                await self.ensure_delay()
                await self.scrape_anime_details_and_characters(anime)

    async def scrape_top_anime_list(self, page_start: int) -> list[str]:
        url = f"https://myanimelist.net/topanime.php?limit={page_start}"
        anime_list = []

        soup = await get_soup_from_url(self.session, url)

        if not soup:
            logger.error(f"Failed to fetch page {page_start}")
            return []

        ranking_rows = soup.find_all('tr', class_='ranking-list')
        for row in ranking_rows:
            try:
                anime_url = self.extract_anime_url(row)
            except Exception as e:
                logger.error(f"Error processing anime row: {e}")
                continue
            if not anime_url:
                logger.warning(f"Failed to extract anime URL from row: {row}")
                continue
            anime_list.append(anime_url)

        return anime_list

    def extract_anime_url(self, row) -> str:
        title_cell = row.find('td', class_='title')
        title_h3 = title_cell.find('h3', class_='anime_ranking_h3')
        if title_h3:
            title_link = title_h3.find('a')
        else:
            title_link = title_cell.find('a', class_='hoverinfo_trigger')

        anime_url = title_link.get('href')
        if anime_url and not anime_url.startswith('http'):
            anime_url = urljoin("https://myanimelist.net", anime_url)
        return anime_url

    async def scrape_anime_details_and_characters(self, anime_url: str, delay: float = 1.0) -> None:
        # Scrape anime details
        # TODO: this should be in the same class probably
        anime = await fetch_and_insert_anime_data(self.session, anime_url)
        if not anime:
            logger.error(f"Failed to scrape anime details from {anime_url}")
            return None

        # Add delay to be respectful to the server
        time.sleep(delay)

        # Create characters URL by appending /characters
        characters_url = anime_url.rstrip('/') + '/characters'
        await fetch_and_insert_actors_data(self.session, characters_url, anime.id)
        return None


async def run_scraper():
    async with aiohttp.ClientSession() as session:
        scraper = MALScraper(session)
        tasks = [scraper.run(i) for i in range(0, ANIME_TO_SCRAPE, ANIME_PER_PAGE)]
        await asyncio.gather(*tasks, return_exceptions=True)

if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(run_scraper())
