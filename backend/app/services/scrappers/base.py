from bs4 import BeautifulSoup
import requests

from app.db.models import Actor, Character, CharacterActor

from app.db.base import get_session
from sqlmodel import select

def get_soup_from_url(url: str) -> BeautifulSoup:
    """Fetch HTML content from a given URL."""
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an error for bad responses
        return BeautifulSoup(response.text, 'html.parser')
    except requests.RequestException as e:
        print(f"Error fetching {url}: {e}")
        return None
