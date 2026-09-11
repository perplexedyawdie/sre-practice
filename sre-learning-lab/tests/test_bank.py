from __future__ import annotations

import json
import random
from pathlib import Path

import pytest
import yaml

from bank import (
    BankValidationError,
    build_scenario_document,
    choose_scenario,
    load_bank,
    load_bank_text,
    score_rubric,
    validate_bank_against_flags,
)


APP_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = APP_DIR.parent
BANK_PATH = APP_DIR / "question_banks/ecommerce.yaml"
FLAG_PATH = REPO_ROOT / "src/flagd/demo.flagd.json"


def test_default_bank_has_four_levels_and_twelve_scenarios() -> None:
    bank = load_bank(BANK_PATH)
    document = json.loads(FLAG_PATH.read_text(encoding="utf-8"))

    validate_bank_against_flags(bank, document)

    assert len(bank.levels) == 4
    assert len(bank.scenarios) == 12
    assert [len(bank.scenarios_for_level(level.id)) for level in bank.levels] == [3, 3, 3, 3]


def test_rejects_duplicate_scenario_ids_and_unknown_level() -> None:
    raw = yaml.safe_load(BANK_PATH.read_text(encoding="utf-8"))
    raw["scenarios"][1]["id"] = raw["scenarios"][0]["id"]
    raw["scenarios"][1]["level"] = "missing"

    with pytest.raises(BankValidationError) as captured:
        load_bank_text(yaml.safe_dump(raw, sort_keys=False))

    assert "scenario IDs must be unique" in captured.value.errors
    assert any("unknown level" in error for error in captured.value.errors)


def test_rejects_malformed_yaml() -> None:
    with pytest.raises(BankValidationError, match="Invalid YAML"):
        load_bank_text("scenarios: [unterminated")


def test_rejects_unknown_live_path_and_variant() -> None:
    bank = load_bank(BANK_PATH)
    document = json.loads(FLAG_PATH.read_text(encoding="utf-8"))
    del document["flags"]["paymentFailure"]

    with pytest.raises(BankValidationError) as captured:
        validate_bank_against_flags(bank, document)

    assert any("paymentFailure" in error for error in captured.value.errors)


def test_build_scenario_resets_flags_and_handles_nested_targeting() -> None:
    bank = load_bank(BANK_PATH)
    document = json.loads(FLAG_PATH.read_text(encoding="utf-8"))
    document["flags"]["adFailure"]["defaultVariant"] = "on"

    scenario = bank.scenario("segmented-catalog")
    applied = build_scenario_document(document, bank, scenario)

    assert applied["flags"]["adFailure"]["defaultVariant"] == "off"
    assert applied["flags"]["productCatalogFailure"]["targeting"]["if"][1] == "on"
    assert document["flags"]["adFailure"]["defaultVariant"] == "on"
    assert document["flags"]["productCatalogFailure"]["targeting"]["if"][1] == "off"


def test_selection_prefers_incomplete_then_allows_review() -> None:
    bank = load_bank(BANK_PATH)
    scenarios = bank.scenarios_for_level("foundations")
    completed = {scenarios[0].id, scenarios[1].id}

    selected = choose_scenario(bank, "foundations", completed, random.Random(7))
    reviewed = choose_scenario(bank, "foundations", {scenario.id for scenario in scenarios}, random.Random(7))

    assert selected.id == scenarios[2].id
    assert reviewed in scenarios


def test_rubric_scoring() -> None:
    scenario = load_bank(BANK_PATH).scenarios[0]
    checked = {scenario.rubric[0]["id"], scenario.rubric[2]["id"]}

    assert score_rubric(scenario.rubric, checked) == 50

