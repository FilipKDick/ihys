from datetime import datetime
from typing import Optional

from pydantic import BaseModel


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
