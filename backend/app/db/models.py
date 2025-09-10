from datetime import datetime

from sqlalchemy import TIMESTAMP
from sqlmodel import (
    Column,
    Field,
    SQLModel,
)


class User(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    mal_id: str = Field(unique=True, index=True, nullable=False)
    mal_username: str = Field(nullable=False)
    encrypted_access_token: str = Field(nullable=False)
    encrypted_refresh_token: str = Field(nullable=False)
    token_expires_at: datetime = Field(
        sa_column=Column(TIMESTAMP(timezone=True), nullable=False),
    )


class Actor(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(unique=True, index=True, nullable=False)
    photo: str = Field(nullable=False)


class Character(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(unique=True, index=True, nullable=False)
    photo: str = Field(nullable=False)
    anime_id: int = Field(foreign_key='anime.id', nullable=False)


class CharacterActor(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    character_id: int = Field(foreign_key='character.id', nullable=False)
    actor_id: int = Field(foreign_key='actor.id', nullable=False)


# TODO: clean data (i.e. season 2 etc)
class Anime(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(unique=True, index=True, nullable=False)
    english_title: str | None = Field(default=None, nullable=True)
    japanese_title: str | None = Field(default=None, nullable=True)
    episodes: str | None = Field(default=None, nullable=True)
    status: str | None = Field(default=None, nullable=True)
    aired: str | None = Field(default=None, nullable=True)
    source: str | None = Field(default=None, nullable=True)
    genres: str | None = Field(default=None, nullable=True)
    themes: str | None = Field(default=None, nullable=True)
    duration: str | None = Field(default=None, nullable=True)
    rating: str | None = Field(default=None, nullable=True)
    score: str | None = Field(default=None, nullable=True)
    ranked: str | None = Field(default=None, nullable=True)
    popularity: str | None = Field(default=None, nullable=True)
    synopsis: str | None = Field(default=None, nullable=True)
