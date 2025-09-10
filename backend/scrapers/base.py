from bs4 import BeautifulSoup
from aiohttp import ClientSession

async def get_soup_from_url(session: ClientSession, url: str) -> BeautifulSoup:
    async with session.get(url) as response:
        response.raise_for_status()
        return BeautifulSoup(response.text, 'html.parser')
