import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

def required_setting(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"{name} is required. Copy .env.example to .env and configure it.")
    return value


def boolean_setting(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


def positive_int_setting(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        parsed_value = int(value)
    except ValueError as error:
        raise RuntimeError(f"{name} must be a positive integer.") from error
    if parsed_value < 1:
        raise RuntimeError(f"{name} must be a positive integer.")
    return parsed_value


DATABASE_URL = required_setting("DATABASE_URL")
DATABASE_POOL_MIN_SIZE = positive_int_setting("DATABASE_POOL_MIN_SIZE", 1)
DATABASE_POOL_MAX_SIZE = positive_int_setting("DATABASE_POOL_MAX_SIZE", 10)
if DATABASE_POOL_MAX_SIZE < DATABASE_POOL_MIN_SIZE:
    raise RuntimeError("DATABASE_POOL_MAX_SIZE must be greater than or equal to DATABASE_POOL_MIN_SIZE.")

SECRET_KEY = required_setting("AUTH_SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_SLIDING_DAYS = 7
REFRESH_TOKEN_MAX_SESSION_DAYS = 30

REDIS_URL = os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0")
OBJECT_STORAGE_ENDPOINT = os.getenv("OBJECT_STORAGE_ENDPOINT")
OBJECT_STORAGE_ACCESS_KEY = os.getenv("OBJECT_STORAGE_ACCESS_KEY")
OBJECT_STORAGE_SECRET_KEY = os.getenv("OBJECT_STORAGE_SECRET_KEY")
OBJECT_STORAGE_BUCKET = os.getenv("OBJECT_STORAGE_BUCKET", "ai-platform-private")
OBJECT_STORAGE_SECURE = boolean_setting("OBJECT_STORAGE_SECURE", False)

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
BGE_MODEL_NAME = os.getenv("BGE_MODEL_NAME", "BAAI/bge-m3")
