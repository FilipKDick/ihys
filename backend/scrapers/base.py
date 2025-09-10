from bs4 import BeautifulSoup
from aiohttp import ClientSession
from typing import Optional

async def get_soup_from_url(session: ClientSession, url: str) -> Optional[BeautifulSoup]:
    """Fetch HTML content from URL and return BeautifulSoup object."""
    async with session.get(url) as response:
        response.raise_for_status()
        html_content = await response.text()
        return BeautifulSoup(html_content, 'html.parser')
