import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root
_project_root = Path(__file__).parent.parent
load_dotenv(_project_root / ".env")


def get_firecrawl_api_key() -> str | None:
    return os.environ.get("FIRECRAWL_API_KEY") or None


def get_database_path() -> str:
    return os.environ.get("DATABASE_PATH", "data/tension974.db")


def get_searches_config_path() -> str:
    return os.environ.get("SEARCHES_CONFIG_PATH", "config/searches.yaml")


def get_log_level() -> str:
    return os.environ.get("LOG_LEVEL", "INFO")


def get_log_file() -> str:
    return os.environ.get("LOG_FILE", "logs/tension974.log")


def get_google_service_account_json() -> str | None:
    return os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON") or None


def get_google_sheet_id() -> str | None:
    return os.environ.get("GOOGLE_SHEET_ID") or None
