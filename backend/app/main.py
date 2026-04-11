from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from app.api import anime, auth, user_anime
from app.core.config import settings

app = FastAPI()

origins = [
    'http://localhost:3000',
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

app.add_middleware(SessionMiddleware, secret_key=settings.ENCRYPTION_KEY.decode())

app.include_router(auth.router, prefix='/api/auth', tags=['Authentication'])
app.include_router(user_anime.router, prefix='/api/user', tags=['User Anime'])
app.include_router(anime.router, prefix='/api/anime', tags=['Anime'])


@app.get('/')
def read_root() -> dict:
    return {'status': 'Backend is running!'}
