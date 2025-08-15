import os


def _normalize_db_uri(uri: str) -> str:
    if uri.startswith("postgres://"):
        return uri.replace("postgres://", "postgresql+psycopg://", 1)
    if uri.startswith("postgresql://"):
        return uri.replace("postgresql://", "postgresql+psycopg://", 1)
    return uri


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-later")
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///site.db")
    SQLALCHEMY_DATABASE_URI = _normalize_db_uri(DATABASE_URL)
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    ARTICLES_PER_PAGE = int(os.getenv("ARTICLES_PER_PAGE", "10"))
    WTF_CSRF_ENABLED = True


class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_ECHO = os.getenv("SQLALCHEMY_ECHO", "0") == "1"


class TestingConfig(Config):
    TESTING = True
    WTF_CSRF_ENABLED = False


class ProductionConfig(Config):
    DEBUG = False
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
