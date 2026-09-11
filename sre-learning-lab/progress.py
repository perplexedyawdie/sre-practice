"""Atomic local persistence for learning progress."""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def atomic_write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent, text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(value, handle, indent=2, sort_keys=True)
            handle.write("\n")
        os.replace(temporary_name, path)
    finally:
        temporary = Path(temporary_name)
        if temporary.exists():
            temporary.unlink()


class ProgressStore:
    def __init__(self, path: str | Path):
        self.path = Path(path)

    def read(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"schema_version": 1, "banks": {}}
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            raise ValueError(f"Cannot read progress file {self.path}: {exc}") from exc
        if not isinstance(data, dict) or data.get("schema_version") != 1 or not isinstance(data.get("banks"), dict):
            raise ValueError(f"Unsupported progress file format in {self.path}")
        return data

    def completed_ids(self, bank_id: str) -> set[str]:
        bank = self.read()["banks"].get(bank_id, {})
        scenarios = bank.get("scenarios", {}) if isinstance(bank, dict) else {}
        return {scenario_id for scenario_id, record in scenarios.items() if record.get("completed") is True}

    def scenario_record(self, bank_id: str, scenario_id: str) -> dict[str, Any]:
        return self.read()["banks"].get(bank_id, {}).get("scenarios", {}).get(scenario_id, {})

    def save_submission(
        self,
        bank_id: str,
        scenario_id: str,
        answers: dict[str, str],
        checked_rubric_ids: set[str],
        score: int,
    ) -> None:
        data = self.read()
        bank = data["banks"].setdefault(bank_id, {"scenarios": {}})
        bank.setdefault("scenarios", {})[scenario_id] = {
            "completed": True,
            "score": score,
            "answers": answers,
            "checked_rubric_ids": sorted(checked_rubric_ids),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        atomic_write_json(self.path, data)

    def reset_bank(self, bank_id: str) -> None:
        data = self.read()
        data["banks"].pop(bank_id, None)
        atomic_write_json(self.path, data)

