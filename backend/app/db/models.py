from datetime import datetime
import uuid

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

    __tablename__ = "user"
    __unique_fields__ = ["username"]


class Actor(DataBaseModel):
    id: int | None = None
    name: str
    photo: str
    created_at: datetime | None = None

    __tablename__ = "actor"
    __unique_fields__ = ["name"]


class Character(DataBaseModel):
    id: int | None = None
    name: str
    photo: str
    anime_id: int
    created_at: datetime | None = None

    __tablename__ = "character"
    __unique_fields__ = ["name", "anime_id"]


class CharacterActor(DataBaseModel):
    id: int | None = None
    character_id: int
    actor_id: int

    __tablename__ = "character_actor"
    __unique_fields__ = ["character_id", "actor_id"]


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
    created_at: datetime | None = None
    updated_at: datetime | None = None

    __tablename__ = "anime"
    __unique_fields__ = ["name"]


class TableNames:
    USERS = "users"
    ACTORS = "actors"
    CHARACTERS = "characters"
    CHARACTER_ACTORS = "character_actors"
    ANIME = "anime"
