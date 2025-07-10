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
