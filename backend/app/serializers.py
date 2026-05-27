from datetime import datetime
from typing import Self

from pydantic import BaseModel, ConfigDict


class UserResponse(BaseModel):
    id: int
    mal_id: str
    mal_username: str
    auth_user_id: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ActorResponse(BaseModel):
    id: int
    name: str
    photo: str
    created_at: datetime | None = None


class CharacterResponse(BaseModel):
    id: int
    name: str
    photo: str
    anime_id: int
    created_at: datetime | None = None


class CharacterActorResponse(BaseModel):
    id: int
    character_id: int
    actor_id: int


class AuthUserResponse(BaseModel):
    id: int
    username: str


class AnimeSummaryResponse(BaseModel):
    id: int
    name: str
    mal_id: int | None = None


class UserAnimeResponse(BaseModel):
    id: int
    anime: AnimeSummaryResponse
    watch_status: str
    score: int | None = None
    episodes_watched: int | None = None
    start_date: datetime | None = None
    finish_date: datetime | None = None
    is_synced_from_mal: bool = False

    @classmethod
    def from_records(cls, user_anime: dict, anime: dict) -> Self:
        return cls(
            id=user_anime['id'],
            anime=AnimeSummaryResponse(
                id=anime['id'],
                name=anime['name'],
                mal_id=anime.get('mal_id'),
            ),
            watch_status=user_anime['watch_status'],
            score=user_anime.get('score'),
            episodes_watched=user_anime.get('episodes_watched'),
            start_date=user_anime.get('start_date'),
            finish_date=user_anime.get('finish_date'),
            is_synced_from_mal=user_anime.get('is_synced_from_mal', False),
        )


class SyncMalStatsResponse(BaseModel):
    created: int
    updated: int
    actor_scraped: int
    actor_skipped: int
    actor_failed: int
    total: int


class SyncMalResponse(BaseModel):
    message: str
    stats: SyncMalStatsResponse


class ActorBriefResponse(BaseModel):
    id: int
    name: str
    photo: str | None = None


class CharacterBriefResponse(BaseModel):
    id: int
    name: str
    photo: str | None = None


class AppearsInEntryResponse(BaseModel):
    id: int
    name: str
    mal_id: int | None = None
    watch_status: str
    character_name: str
    character_photo: str | None = None


class ActorOverlapResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    actor: ActorBriefResponse
    character_in_new_anime: CharacterBriefResponse | None = None
    appears_in: list[AppearsInEntryResponse]


class AnimeSearchResultResponse(BaseModel):
    mal_id: int
    title: str
    image: str | None = None
    year: str | None = None
