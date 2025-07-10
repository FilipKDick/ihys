from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query
from sqlmodel import Field, Session, SQLModel, create_engine, select


class User(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    mal_id: str = Field(unique=True, index=True, nullable=False)
    mal_username: str = Field(nullable=False)
    encrypted_access_token: str = Field(nullable=False)
    encrypted_refresh_token: str = Field(nullable=False)
    token_expires_at: str = Field(nullable=False)