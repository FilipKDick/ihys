import uuid

from datetime import datetime
from typing import ClassVar

from app.db.base import DataBaseModel


class User(DataBaseModel):
    id: int | None = None
    mal_id: str
    mal_username: str
    encrypted_access_token: str
    encrypted_refresh_token: str
    token_expires_at: datetime
    auth_user_id: uuid.UUID | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    __tablename__ = 'users'
    __unique_fields__: ClassVar[list[str]] = ['mal_id']


class Actor(DataBaseModel):
    id: int | None = None
    name: str
    photo: str
    created_at: datetime | None = None

    __tablename__ = 'actors'
    __unique_fields__: ClassVar[list[str]] = ['name']


class Character(DataBaseModel):
    id: int | None = None
    name: str
    photo: str
    anime_id: int
    created_at: datetime | None = None

    __tablename__ = 'characters'
    __unique_fields__: ClassVar[list[str]] = ['name', 'anime_id']


class CharacterActor(DataBaseModel):
    id: int | None = None
    character_id: int
    actor_id: int

    __tablename__ = 'character_actors'
    __unique_fields__: ClassVar[list[str]] = ['character_id', 'actor_id']


# TODO: clean data (i.e. season 2 etc)
class Anime(DataBaseModel):
    id: int | None = None
    name: str
    english_title: str | None = None
    japanese_title: str | None = None
    episodes: str | None = None
    status: str | None = None
    aired: str | None = None
    source: str | None = None
    genres: str | None = None
    themes: str | None = None
    duration: str | None = None
    rating: str | None = None
    score: str | None = None
    ranked: str | None = None
    popularity: str | None = None
    synopsis: str | None = None
    mal_id: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    __tablename__ = 'anime'
    __unique_fields__: ClassVar[list[str]] = ['name']


class UserAnime(DataBaseModel):
    id: int | None = None
    user_id: int
    anime_id: int
    mal_anime_id: int | None = None
    watch_status: str = 'completed'
    score: int | None = None
    episodes_watched: int | None = None
    start_date: datetime | None = None
    finish_date: datetime | None = None
    is_synced_from_mal: bool = False
    created_at: datetime | None = None
    updated_at: datetime | None = None

    __tablename__ = 'user_anime'
    __unique_fields__: ClassVar[list[str]] = ['user_id', 'anime_id']


class TableNames:
    USERS = 'users'
    ACTORS = 'actors'
    CHARACTERS = 'characters'
    CHARACTER_ACTORS = 'character_actors'
    ANIME = 'anime'
    USER_ANIME = 'user_anime'
