"""Safe activation and recovery for Astronomy Shop flagd scenarios."""

from __future__ import annotations

import json
import os
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

from bank import QuestionBank, Scenario, build_scenario_document, validate_bank_against_flags
from progress import atomic_write_json


class FlagManagerError(RuntimeError):
    pass


class ActiveScenarioError(FlagManagerError):
    pass


class RestoreConflictError(FlagManagerError):
    pass


@dataclass(frozen=True)
class LabConfig:
    shop_url: str
    flag_api_url: str
    grafana_url: str
    jaeger_url: str
    loadgen_url: str
    flag_file: Path
    state_dir: Path

    @classmethod
    def from_environment(cls, app_dir: Path) -> "LabConfig":
        shop_url = os.getenv("SRE_LAB_SHOP_URL", "http://localhost:8080").rstrip("/")
        return cls(
            shop_url=shop_url,
            flag_api_url=os.getenv("SRE_LAB_FLAG_API_URL", f"{shop_url}/feature/api").rstrip("/"),
            grafana_url=os.getenv("SRE_LAB_GRAFANA_URL", f"{shop_url}/grafana/").rstrip("/") + "/",
            jaeger_url=os.getenv("SRE_LAB_JAEGER_URL", f"{shop_url}/jaeger/").rstrip("/") + "/",
            loadgen_url=os.getenv("SRE_LAB_LOADGEN_URL", f"{shop_url}/loadgen/").rstrip("/") + "/",
            flag_file=Path(os.getenv("SRE_LAB_FLAG_FILE", str(app_dir.parent / "src/flagd/demo.flagd.json"))).resolve(),
            state_dir=Path(os.getenv("SRE_LAB_STATE_DIR", str(app_dir / ".state"))).resolve(),
        )


def atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent, text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(content)
        os.replace(temporary_name, path)
    finally:
        temporary = Path(temporary_name)
        if temporary.exists():
            temporary.unlink()


class FlagManager:
    def __init__(self, config: LabConfig, session: requests.Session | Any | None = None):
        self.config = config
        self.session = session or requests.Session()
        self.active_path = config.state_dir / "active-session.json"

    def read_source(self) -> tuple[str, dict[str, Any]]:
        try:
            content = self.config.flag_file.read_text(encoding="utf-8")
            document = json.loads(content)
        except (OSError, json.JSONDecodeError) as exc:
            raise FlagManagerError(f"Cannot read {self.config.flag_file}: {exc}") from exc
        if not isinstance(document, dict) or not isinstance(document.get("flags"), dict):
            raise FlagManagerError("The local flag document must contain a flags mapping")
        return content, document

    def fetch_live(self) -> dict[str, Any]:
        try:
            response = self.session.get(f"{self.config.flag_api_url}/read", timeout=3)
            response.raise_for_status()
            document = response.json()
        except (requests.RequestException, ValueError) as exc:
            raise FlagManagerError(f"Cannot reach the flag API: {exc}") from exc
        if not isinstance(document, dict) or not isinstance(document.get("flags"), dict):
            raise FlagManagerError("Flag API returned an invalid document")
        return document

    def write_live(self, document: dict[str, Any], timeout_seconds: float = 6) -> None:
        try:
            response = self.session.post(
                f"{self.config.flag_api_url}/write",
                json={"data": document},
                timeout=3,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            raise FlagManagerError(f"Flag update failed: {exc}") from exc

        deadline = time.monotonic() + timeout_seconds
        expected_flags = document.get("flags", {})
        while time.monotonic() < deadline:
            if self.fetch_live().get("flags") == expected_flags:
                return
            time.sleep(0.1)
        raise FlagManagerError("Flag API accepted the update but did not expose it before the timeout")

    def health(self) -> tuple[bool, str]:
        try:
            live = self.fetch_live()
            return True, f"Connected to flagd UI ({len(live['flags'])} flags)"
        except FlagManagerError as exc:
            return False, str(exc)

    def active_session(self) -> dict[str, Any] | None:
        if not self.active_path.exists():
            return None
        try:
            value = json.loads(self.active_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise FlagManagerError(f"Cannot read recovery state {self.active_path}: {exc}") from exc
        if not isinstance(value, dict) or value.get("schema_version") != 1:
            raise FlagManagerError(f"Unsupported recovery state in {self.active_path}")
        return value

    def activate(self, bank: QuestionBank, scenario: Scenario) -> None:
        if self.active_session() is not None:
            raise ActiveScenarioError("Restore or close the current active scenario first")
        original_text, original = self.read_source()
        validate_bank_against_flags(bank, original)
        applied = build_scenario_document(original, bank, scenario)
        state = {
            "schema_version": 1,
            "bank_id": bank.id,
            "scenario_id": scenario.id,
            "activated_at": datetime.now(timezone.utc).isoformat(),
            "original_text": original_text,
            "original_document": original,
            "applied_document": applied,
        }
        atomic_write_json(self.active_path, state)
        self.write_live(applied)

    def restore_has_conflict(self) -> bool:
        active = self.active_session()
        if active is None:
            return False
        live = self.fetch_live()
        return live.get("flags") != active["applied_document"].get("flags")

    def restore(self, force: bool = False) -> None:
        active = self.active_session()
        if active is None:
            raise FlagManagerError("There is no active scenario to restore")
        if not force and self.restore_has_conflict():
            raise RestoreConflictError("Flags changed outside this app after scenario activation")
        original = active["original_document"]
        self.write_live(original)
        atomic_write_text(self.config.flag_file, active["original_text"])
        self.active_path.unlink(missing_ok=True)

    def keep_current_and_close(self) -> None:
        if self.active_session() is None:
            raise FlagManagerError("There is no active scenario")
        self.active_path.unlink(missing_ok=True)

