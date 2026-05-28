import logging

import sentry_sdk
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from app.api import anime, auth, user_anime
from app.core.config import settings


def configure_logging() -> None:
    level_name = settings.LOG_LEVEL.upper()
    level = logging.getLevelNamesMapping().get(level_name, logging.INFO)
    logging.basicConfig(
        level=level,
        format='%(asctime)s %(levelname)s [%(name)s] %(message)s',
    )


configure_logging()

if settings.SENTRY_DSN:
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        traces_sample_rate=0.1,
        send_default_pii=False,
        environment='production' if not settings.DEBUG else 'development',
    )

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL],
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
