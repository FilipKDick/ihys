from sqlalchemy import Column, Integer, String, DateTime
from app.db.base import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    mal_id = Column(String, unique=True, index=True, nullable=False)
    mal_username = Column(String, nullable=False)
    
    encrypted_access_token = Column(String, nullable=False)
    encrypted_refresh_token = Column(String, nullable=False)
    
    token_expires_at = Column(DateTime, nullable=False)