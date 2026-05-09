from datetime import datetime
from typing import Optional
from urllib.parse import urlparse

from pydantic import BaseModel, field_validator


class AnimeResponse(BaseModel):
    id: int
    name: str
    english_title: Optional[str] = None
    japanese_title: Optional[str] = None
    episodes: Optional[str] = None
    status: Optional[str] = None
    aired: Optional[str] = None
    score: Optional[str] = None
    synopsis: Optional[str] = None
    mal_id: Optional[int] = None


class UserAnimeResponse(BaseModel):
    id: int
    anime: AnimeResponse
    watch_status: str
    score: Optional[int] = None
    episodes_watched: Optional[int] = None
    start_date: Optional[str] = None
    finish_date: Optional[str] = None
    is_synced_from_mal: bool


class AddAnimeRequest(BaseModel):
    anime_name: str
    anime_url: Optional[str] = None
    watch_status: str = 'completed'
    score: Optional[int] = None
    episodes_watched: Optional[int] = None
    start_date: Optional[str] = None
    finish_date: Optional[str] = None

    @field_validator('anime_url')
    @classmethod
    def anime_url_must_be_mal(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        parsed = urlparse(v)
        if parsed.hostname != 'myanimelist.net':
            raise ValueError('anime_url must be a myanimelist.net URL')
        return v


class UpdateAnimeRequest(BaseModel):
    watch_status: Optional[str] = None
    score: Optional[int] = None
    episodes_watched: Optional[int] = None
    start_date: Optional[str] = None
    finish_date: Optional[str] = None


class UserResponse(BaseModel):
    id: int
    mal_id: str
    mal_username: str
    auth_user_id: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class ActorResponse(BaseModel):
    id: int
    name: str
    photo: str
    created_at: Optional[datetime] = None


class CharacterResponse(BaseModel):
    id: int
    name: str
    photo: str
    anime_id: int
    created_at: Optional[datetime] = None


class CharacterActorResponse(BaseModel):
    id: int
    character_id: int
    actor_id: int
