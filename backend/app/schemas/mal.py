from datetime import date, datetime, timezone

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
