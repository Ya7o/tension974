import json
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any

from . import database
from .models import Observation, SearchConfig


class StorageError(RuntimeError):
    pass


class Storage(ABC):
    @abstractmethod
    def initialize(self) -> None:
        pass

    @abstractmethod
    def upsert_search(self, search: SearchConfig) -> None:
        pass

    @abstractmethod
    def insert_observation(self, obs: Observation) -> int:
        pass

    @abstractmethod
    def start_run(self, provider: str) -> int:
        pass

    @abstractmethod
    def finish_run(self, run_id: int, status: str, error_message: str | None = None) -> None:
        pass


class SQLiteStorage(Storage):
    def __init__(self, db_path: str):
        self.db_path = db_path

    def initialize(self) -> None:
        database.init_db(self.db_path)

    def upsert_search(self, search: SearchConfig) -> None:
        database.upsert_search(self.db_path, search)

    def insert_observation(self, obs: Observation) -> int:
        return database.insert_observation(self.db_path, obs)

    def start_run(self, provider: str) -> int:
        return database.start_collection_run(self.db_path, provider)

    def finish_run(self, run_id: int, status: str, error_message: str | None = None) -> None:
        database.finish_collection_run(self.db_path, run_id, status, error_message)


class GoogleSheetsStorage(Storage):
    OBSERVATIONS_WORKSHEET = "observations"
    RUNS_WORKSHEET = "runs"

    OBSERVATION_HEADERS = [
        "search_id",
        "observed_at",
        "total_listings_count",
        "raw_total_listings_text",
        "median_price",
        "average_price",
        "price_sample_size",
        "min_price",
        "max_price",
        "status",
        "provider",
        "error_message",
        "credits_used",
        "created_at",
    ]
    RUN_HEADERS = [
        "started_at",
        "finished_at",
        "status",
        "provider",
        "error_message",
    ]

    def __init__(self, service_account_json: str | None, sheet_id: str | None):
        if not service_account_json:
            raise StorageError("GOOGLE_SERVICE_ACCOUNT_JSON est manquant.")
        if not sheet_id:
            raise StorageError("GOOGLE_SHEET_ID est manquant.")

        try:
            service_account_info = json.loads(service_account_json)
        except json.JSONDecodeError as exc:
            raise StorageError("GOOGLE_SERVICE_ACCOUNT_JSON n'est pas un JSON valide.") from exc

        try:
            import gspread
        except ImportError as exc:
            raise StorageError(
                "Les dépendances Google Sheets sont absentes. Installe gspread et google-auth."
            ) from exc

        try:
            client = gspread.service_account_from_dict(service_account_info)
            self.sheet = client.open_by_key(sheet_id)
        except Exception as exc:
            raise StorageError(f"Connexion Google Sheets impossible: {exc}") from exc

    def initialize(self) -> None:
        self.observations = self._worksheet(
            self.OBSERVATIONS_WORKSHEET,
            self.OBSERVATION_HEADERS,
        )
        self.runs = self._worksheet(self.RUNS_WORKSHEET, self.RUN_HEADERS)

    def upsert_search(self, search: SearchConfig) -> None:
        return None

    def insert_observation(self, obs: Observation) -> int:
        created_at = obs.created_at or _now_iso()
        row = [
            obs.search_id,
            obs.observed_at,
            _cell(obs.total_listings_count),
            _cell(obs.raw_total_listings_text),
            _cell(obs.median_price),
            _cell(obs.average_price),
            _cell(obs.price_sample_size),
            _cell(obs.min_price),
            _cell(obs.max_price),
            obs.status,
            obs.provider,
            _cell(obs.error_message),
            _cell(obs.credits_used),
            created_at,
        ]
        self.observations.append_row(row, value_input_option="USER_ENTERED")
        return len(self.observations.get_all_values())

    def start_run(self, provider: str) -> int:
        started_at = _now_iso()
        row = [started_at, "", "running", provider, ""]
        self.runs.append_row(row, value_input_option="USER_ENTERED")
        return len(self.runs.get_all_values())

    def finish_run(self, run_id: int, status: str, error_message: str | None = None) -> None:
        self.runs.update(
            [[
                _cell(self.runs.cell(run_id, 1).value),
                _now_iso(),
                status,
                _cell(self.runs.cell(run_id, 4).value),
                _cell(error_message),
            ]],
            range_name=f"A{run_id}:E{run_id}",
        )

    def _worksheet(self, title: str, headers: list[str]):
        try:
            worksheet = self.sheet.worksheet(title)
        except Exception:
            worksheet = self.sheet.add_worksheet(title=title, rows=1000, cols=len(headers))

        first_row = worksheet.row_values(1)
        if first_row != headers:
            worksheet.update([headers], range_name="A1")
        return worksheet


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _cell(value: Any) -> Any:
    return "" if value is None else value
