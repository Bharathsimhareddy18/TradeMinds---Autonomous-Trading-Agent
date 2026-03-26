from pydantic_settings import BaseSettings
from supabase import create_client, Client
from openai import OpenAI
from app.logger import get_logger

logger = get_logger(__name__)


class Settings(BaseSettings):
    # Supabase
    SUPABASE_PROJECT_URL: str
    SUPABASE_ANON_KEY: str

    # OpenAI
    OPENAI_API_KEY: str

    # Trading Constants
    STARTING_BALANCE: float = 100000.0
    MIN_TRADE: float = 100.0
    MAX_SCALP_TRADE: float = 10000.0
    MAX_MOMENTUM_TRADE: float = 30000.0
    TRADE_WINDOW_MIN_SECONDS: int = 60
    TRADE_WINDOW_MAX_SECONDS: int = 600

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()

# Single shared clients — import these everywhere
try:
    supabase: Client = create_client(
        settings.SUPABASE_PROJECT_URL,
        settings.SUPABASE_ANON_KEY
    )
except Exception as e:
    logger.warning(f"Failed to initialize Supabase client at import: {e}")
    supabase = None

try:
    openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)
except Exception as e:
    logger.warning(f"Failed to initialize OpenAI client at import: {e}")
    openai_client = None