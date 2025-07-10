from cryptography.fernet import Fernet

from app.core.config import settings

cipher_suite = Fernet(settings.ENCRYPTION_KEY)


def encrypt_token(token: str) -> str:
    return cipher_suite.encrypt(token.encode('utf-8')).decode('utf-8')
