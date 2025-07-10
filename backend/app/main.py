from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from app.api import auth
from app.core.config import settings
from app.db.base import init_db

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

app.add_middleware(SessionMiddleware, secret_key=settings.ENCRYPTION_KEY)

app.include_router(auth.router, prefix='/api/auth', tags=['Authentication'])


@app.on_event('startup')
async def startup_event() -> None:
    print('Starting up the FastAPI application...')
    await init_db()


@app.get('/')
def read_root() -> dict:
    return {'status': 'Backend is running!'}
