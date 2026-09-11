from __future__ import annotations

import json

import pytest

from progress import ProgressStore


def test_progress_round_trip_and_reset(tmp_path) -> None:
    path = tmp_path / "progress.json"
    store = ProgressStore(path)

    store.save_submission(
        "bank-one",
        "scenario-one",
        {"diagnosis": "payment failed"},
        {"trace", "sli"},
        75,
    )

    assert store.completed_ids("bank-one") == {"scenario-one"}
    record = store.scenario_record("bank-one", "scenario-one")
    assert record["score"] == 75
    assert record["answers"]["diagnosis"] == "payment failed"
    assert record["checked_rubric_ids"] == ["sli", "trace"]

    store.reset_bank("bank-one")
    assert store.completed_ids("bank-one") == set()


def test_corrupt_progress_is_reported(tmp_path) -> None:
    path = tmp_path / "progress.json"
    path.write_text("not json", encoding="utf-8")

    with pytest.raises(ValueError, match="Cannot read progress"):
        ProgressStore(path).read()


def test_progress_file_is_valid_json(tmp_path) -> None:
    path = tmp_path / "progress.json"
    ProgressStore(path).save_submission("bank", "scenario", {}, set(), 0)

    assert json.loads(path.read_text(encoding="utf-8"))["schema_version"] == 1

