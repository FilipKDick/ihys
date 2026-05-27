from datetime import date, datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


class MalGenre(BaseModel):
    id: int
    name: str


class MalAnimeNode(BaseModel):
    id: int
    title: str
    num_episodes: int | None = None
    status: str | None = None
    synopsis: str | None = None
    mean: float | None = None
    rank: int | None = None
    popularity: int | None = None
    genres: list[MalGenre] = Field(default_factory=list)

    def to_anime_insert_data(self) -> dict[str, str | int]:
        return {
            'name': self.title,
            'mal_id': self.id,
            'episodes': str(self.num_episodes or ''),
            'status': self.status or '',
            'synopsis': self.synopsis or '',
            'score': str(self.mean or ''),
            'ranked': str(self.rank or ''),
            'popularity': str(self.popularity or ''),
            'genres': ','.join(genre.name for genre in self.genres),
            'created_at': datetime.now(timezone.utc).isoformat(),
        }


class MalListStatus(BaseModel):
    status: str
    score: int | None = None
    num_episodes_watched: int | None = None
    start_date: date | None = None
    finish_date: date | None = None


class MalUserAnimeListEntry(BaseModel):
    node: MalAnimeNode
    list_status: MalListStatus

    def to_user_anime_upsert_data(
        self,
        *,
        user_id: int,
        anime_id: int,
    ) -> dict[str, Any]:
        return {
            'user_id': user_id,
            'anime_id': anime_id,
            'mal_anime_id': self.node.id,
            'watch_status': self.list_status.status,
            'is_synced_from_mal': True,
            'updated_at': datetime.now(timezone.utc).isoformat(),
            'score': self.list_status.score,
            'episodes_watched': self.list_status.num_episodes_watched,
            'start_date': self.list_status.start_date,
            'finish_date': self.list_status.finish_date,
        }

    def to_user_anime_insert_data(
        self,
        *,
        user_id: int,
        anime_id: int,
    ) -> dict[str, Any]:
        data = self.to_user_anime_upsert_data(user_id=user_id, anime_id=anime_id)
        data['created_at'] = datetime.now(timezone.utc).isoformat()
        return data
