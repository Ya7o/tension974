import json
import uuid
from abc import ABC, abstractmethod
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
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
    def start_run(self, provider: str) -> int | str:
        pass

    @abstractmethod
    def finish_run(self, run_id: int | str, status: str, error_message: str | None = None) -> None:
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


class JsonlStorage(Storage):
    """Git-native storage: appends observations/runs as JSON Lines under data/.

    Chosen as the canonical production backend so history lives in the repo
    itself (versioned, diffable, no external account) instead of a separate
    Google Sheet. Files are append-only, which keeps `git diff` readable and
    avoids merge conflicts on concurrent runs.
    """

    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.observations_path = self.data_dir / "observations.jsonl"
        self.runs_path = self.data_dir / "runs.jsonl"

    def initialize(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.observations_path.touch(exist_ok=True)
        self.runs_path.touch(exist_ok=True)

    def upsert_search(self, search: SearchConfig) -> None:
        return None

    def insert_observation(self, obs: Observation) -> int:
        row = asdict(obs)
        row["created_at"] = obs.created_at or _now_iso()
        _append_jsonl(self.observations_path, row)
        return _count_lines(self.observations_path)

    def start_run(self, provider: str) -> str:
        run_id = uuid.uuid4().hex[:12]
        _append_jsonl(self.runs_path, {
            "run_id": run_id,
            "started_at": _now_iso(),
            "finished_at": None,
            "status": "running",
            "provider": provider,
            "error_message": None,
        })
        return run_id

    def finish_run(self, run_id: str, status: str, error_message: str | None = None) -> None:
        _append_jsonl(self.runs_path, {
            "run_id": run_id,
            "started_at": None,
            "finished_at": _now_iso(),
            "status": status,
            "provider": None,
            "error_message": error_message,
        })


def _append_jsonl(path: Path, row: dict[str, Any]) -> None:
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False, sort_keys=True))
        f.write("\n")


def _count_lines(path: Path) -> int:
    with open(path, encoding="utf-8") as f:
        return sum(1 for _ in f)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
