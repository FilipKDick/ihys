from httpx_oauth.oauth2 import OAuth2

from app.core.config import settings

AUTHORIZE_ENDPOINT = 'https://myanimelist.net/v1/oauth2/authorize'
ACCESS_TOKEN_ENDPOINT = 'https://myanimelist.net/v1/oauth2/token'  # noqa: S105


class MyAnimeListOAuth2(OAuth2):
    def __init__(self, client_id: str, client_secret: str):
        super().__init__(
            client_id,
            client_secret,
            AUTHORIZE_ENDPOINT,
            ACCESS_TOKEN_ENDPOINT,
            name='myanimelist',
        )


client = MyAnimeListOAuth2(settings.MAL_CLIENT_ID, settings.MAL_CLIENT_SECRET)
