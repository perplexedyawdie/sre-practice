from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
import requests

from bank import load_bank
from flag_manager import FlagManager, FlagManagerError, LabConfig, RestoreConflictError


APP_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = APP_DIR.parent


class FakeResponse:
    def __init__(self, payload, status_code: int = 200):
        self.payload = payload
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError(f"status {self.status_code}")

    def json(self):
        return copy.deepcopy(self.payload)


class FakeSession:
    def __init__(self, document, fail_post: bool = False):
        self.live = {"flags": copy.deepcopy(document["flags"])}
        self.fail_post = fail_post

    def get(self, _url, timeout):
        return FakeResponse(self.live)

    def post(self, _url, json, timeout):
        if self.fail_post:
            raise requests.ConnectionError("simulated failure")
        self.live = {"flags": copy.deepcopy(json["data"]["flags"])}
        return FakeResponse({})


def make_manager(tmp_path, session: FakeSession) -> tuple[FlagManager, str, dict]:
    original_text = (REPO_ROOT / "src/flagd/demo.flagd.json").read_text(encoding="utf-8")
    original = json.loads(original_text)
    flag_file = tmp_path / "demo.flagd.json"
    flag_file.write_text(original_text, encoding="utf-8")
    config = LabConfig(
        shop_url="http://shop",
        flag_api_url="http://shop/feature/api",
        grafana_url="http://shop/grafana/",
        jaeger_url="http://shop/jaeger/",
        loadgen_url="http://shop/loadgen/",
        flag_file=flag_file,
        state_dir=tmp_path / "state",
    )
    return FlagManager(config, session), original_text, original


def test_activate_isolates_faults_and_restore_is_exact(tmp_path) -> None:
    bank = load_bank(APP_DIR / "question_banks/ecommerce.yaml")
    source = json.loads((REPO_ROOT / "src/flagd/demo.flagd.json").read_text(encoding="utf-8"))
    source["flags"]["adFailure"]["defaultVariant"] = "on"
    session = FakeSession(source)
    manager, original_text, _ = make_manager(tmp_path, session)
    # Match the source file with the externally enabled ad flag.
    changed = json.loads(original_text)
    changed["flags"]["adFailure"]["defaultVariant"] = "on"
    changed_text = json.dumps(changed, indent=2) + "\n"
    manager.config.flag_file.write_text(changed_text, encoding="utf-8")

    manager.activate(bank, bank.scenario("checkout-contract"))

    assert session.live["flags"]["paymentFailure"]["defaultVariant"] == "10%"
    assert session.live["flags"]["adFailure"]["defaultVariant"] == "off"
    assert manager.active_session()["original_text"] == changed_text

    manager.restore()

    assert manager.config.flag_file.read_text(encoding="utf-8") == changed_text
    assert session.live["flags"]["adFailure"]["defaultVariant"] == "on"
    assert manager.active_session() is None


def test_failed_activation_keeps_recovery_snapshot(tmp_path) -> None:
    bank = load_bank(APP_DIR / "question_banks/ecommerce.yaml")
    source = json.loads((REPO_ROOT / "src/flagd/demo.flagd.json").read_text(encoding="utf-8"))
    manager, _, _ = make_manager(tmp_path, FakeSession(source, fail_post=True))

    with pytest.raises(FlagManagerError, match="Flag update failed"):
        manager.activate(bank, bank.scenarios[0])

    assert manager.active_session() is not None


def test_restore_detects_concurrent_change_and_can_force(tmp_path) -> None:
    bank = load_bank(APP_DIR / "question_banks/ecommerce.yaml")
    source = json.loads((REPO_ROOT / "src/flagd/demo.flagd.json").read_text(encoding="utf-8"))
    session = FakeSession(source)
    manager, _, _ = make_manager(tmp_path, session)
    manager.activate(bank, bank.scenarios[0])
    session.live["flags"]["adFailure"]["defaultVariant"] = "on"

    with pytest.raises(RestoreConflictError):
        manager.restore()

    assert manager.active_session() is not None
    manager.restore(force=True)
    assert manager.active_session() is None


def test_keep_current_closes_recovery_without_writing(tmp_path) -> None:
    bank = load_bank(APP_DIR / "question_banks/ecommerce.yaml")
    source = json.loads((REPO_ROOT / "src/flagd/demo.flagd.json").read_text(encoding="utf-8"))
    session = FakeSession(source)
    manager, _, _ = make_manager(tmp_path, session)
    manager.activate(bank, bank.scenarios[0])
    current = copy.deepcopy(session.live)

    manager.keep_current_and_close()

    assert manager.active_session() is None
    assert session.live == current

