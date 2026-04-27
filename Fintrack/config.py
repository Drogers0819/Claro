import os


def _normalize_db_url(url):
    if url and url.startswith("postgres://"):
        return "postgresql://" + url[len("postgres://"):]
    return url


DATABASE_URL = _normalize_db_url(os.environ.get("DATABASE_URL"))


class DevelopmentConfig:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key")
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = DATABASE_URL or "sqlite:///dev.db"
    SEND_FILE_MAX_AGE_DEFAULT = 0  # Disable static file caching in dev


class TestingConfig:
    SECRET_KEY = "test-secret-key"
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False
    RATELIMIT_ENABLED = False


class ProductionConfig:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key")
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = DATABASE_URL or "sqlite:///dev.db"
    RESEND_API_KEY = os.environ.get("RESEND_API_KEY")
