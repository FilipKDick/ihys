import pytest
from pydantic import ValidationError

from app.serializers import AddAnimeRequest


def test_valid_mal_url_accepted():
    req = AddAnimeRequest(
        anime_name='Naruto',
        anime_url='https://myanimelist.net/anime/20/Naruto',
    )
    assert req.anime_url == 'https://myanimelist.net/anime/20/Naruto'


def test_none_url_accepted():
    req = AddAnimeRequest(anime_name='Naruto', anime_url=None)
    assert req.anime_url is None


def test_non_mal_url_rejected():
    with pytest.raises(ValidationError):
        AddAnimeRequest(
            anime_name='Naruto',
            anime_url='http://169.254.169.254/latest/meta-data/',
        )


def test_internal_url_rejected():
    with pytest.raises(ValidationError):
        AddAnimeRequest(
            anime_name='Naruto',
            anime_url='http://localhost:8080/internal',
        )


def test_other_domain_rejected():
    with pytest.raises(ValidationError):
        AddAnimeRequest(
            anime_name='Naruto',
            anime_url='https://evil.com/fake',
        )
