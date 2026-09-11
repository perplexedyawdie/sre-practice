"""Question-bank models, validation, selection, and flag mutations."""

from __future__ import annotations

import copy
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import yaml


class BankValidationError(ValueError):
    """Raised when a question bank does not satisfy the versioned contract."""

    def __init__(self, errors: Iterable[str]):
        self.errors = list(errors)
        super().__init__("; ".join(self.errors))


@dataclass(frozen=True)
class Level:
    id: str
    title: str
    order: int
    objective: str


@dataclass(frozen=True)
class FlagSpec:
    id: str
    path: tuple[str | int, ...]
    variants: tuple[str, ...]
    safe_variant: str


@dataclass(frozen=True)
class Fault:
    flag: str
    variant: str


@dataclass(frozen=True)
class Scenario:
    id: str
    level: str
    title: str
    concepts: tuple[str, ...]
    briefing: str
    critical_user_journey: str
    service_tier: str
    sla: dict[str, Any]
    slos: tuple[dict[str, Any], ...]
    slis: tuple[dict[str, Any], ...]
    error_budget: str
    fault_profile: tuple[Fault, ...]
    observation_minutes: int
    tasks: tuple[str, ...]
    hints: tuple[str, ...]
    solution: dict[str, Any]
    rubric: tuple[dict[str, Any], ...]


@dataclass(frozen=True)
class QuestionBank:
    schema_version: int
    id: str
    title: str
    description: str
    levels: tuple[Level, ...]
    flags: dict[str, FlagSpec]
    scenarios: tuple[Scenario, ...]

    def scenarios_for_level(self, level_id: str) -> list[Scenario]:
        return [scenario for scenario in self.scenarios if scenario.level == level_id]

    def scenario(self, scenario_id: str) -> Scenario:
        for scenario in self.scenarios:
            if scenario.id == scenario_id:
                return scenario
        raise KeyError(scenario_id)


def _required_string(data: dict[str, Any], key: str, location: str, errors: list[str]) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{location}.{key} must be a non-empty string")
        return ""
    return value.strip()


def _string_list(data: dict[str, Any], key: str, location: str, errors: list[str]) -> tuple[str, ...]:
    value = data.get(key)
    if not isinstance(value, list) or not value or not all(isinstance(item, str) and item.strip() for item in value):
        errors.append(f"{location}.{key} must be a non-empty list of strings")
        return ()
    return tuple(item.strip() for item in value)


def load_bank(path: str | Path) -> QuestionBank:
    return load_bank_text(Path(path).read_text(encoding="utf-8"))


def load_bank_text(content: str) -> QuestionBank:
    try:
        raw = yaml.safe_load(content)
    except yaml.YAMLError as exc:
        raise BankValidationError([f"Invalid YAML: {exc}"]) from exc
    return parse_bank(raw)


def parse_bank(raw: Any) -> QuestionBank:
    errors: list[str] = []
    if not isinstance(raw, dict):
        raise BankValidationError(["The bank root must be a mapping"])

    schema_version = raw.get("schema_version")
    if schema_version != 1:
        errors.append("schema_version must be 1")

    metadata = raw.get("bank")
    if not isinstance(metadata, dict):
        metadata = {}
        errors.append("bank must be a mapping")
    bank_id = _required_string(metadata, "id", "bank", errors)
    title = _required_string(metadata, "title", "bank", errors)
    description = _required_string(metadata, "description", "bank", errors)

    levels: list[Level] = []
    raw_levels = raw.get("levels")
    if not isinstance(raw_levels, list) or not raw_levels:
        errors.append("levels must be a non-empty list")
        raw_levels = []
    for index, item in enumerate(raw_levels):
        location = f"levels[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{location} must be a mapping")
            continue
        level_id = _required_string(item, "id", location, errors)
        level_title = _required_string(item, "title", location, errors)
        objective = _required_string(item, "objective", location, errors)
        order = item.get("order")
        if not isinstance(order, int) or order < 1:
            errors.append(f"{location}.order must be a positive integer")
            order = index + 1
        levels.append(Level(level_id, level_title, order, objective))

    level_ids = [level.id for level in levels]
    if len(level_ids) != len(set(level_ids)):
        errors.append("level IDs must be unique")
    orders = [level.order for level in levels]
    if len(orders) != len(set(orders)):
        errors.append("level order values must be unique")

    flags: dict[str, FlagSpec] = {}
    raw_flags = raw.get("flag_catalog")
    if not isinstance(raw_flags, dict) or not raw_flags:
        errors.append("flag_catalog must be a non-empty mapping")
        raw_flags = {}
    for flag_id, item in raw_flags.items():
        location = f"flag_catalog.{flag_id}"
        if not isinstance(flag_id, str) or not flag_id:
            errors.append("flag_catalog keys must be non-empty strings")
            continue
        if not isinstance(item, dict):
            errors.append(f"{location} must be a mapping")
            continue
        path = item.get("path")
        if not isinstance(path, list) or not path or not all(isinstance(part, (str, int)) for part in path):
            errors.append(f"{location}.path must be a non-empty list of string/integer path components")
            path = []
        variants = _string_list(item, "variants", location, errors)
        safe_variant = _required_string(item, "safe_variant", location, errors)
        if safe_variant and variants and safe_variant not in variants:
            errors.append(f"{location}.safe_variant must be listed in variants")
        flags[flag_id] = FlagSpec(flag_id, tuple(path), variants, safe_variant)

    scenarios: list[Scenario] = []
    raw_scenarios = raw.get("scenarios")
    if not isinstance(raw_scenarios, list) or not raw_scenarios:
        errors.append("scenarios must be a non-empty list")
        raw_scenarios = []
    for index, item in enumerate(raw_scenarios):
        location = f"scenarios[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{location} must be a mapping")
            continue
        scenario_id = _required_string(item, "id", location, errors)
        level = _required_string(item, "level", location, errors)
        scenario_title = _required_string(item, "title", location, errors)
        concepts = _string_list(item, "concepts", location, errors)
        briefing = _required_string(item, "briefing", location, errors)
        journey = _required_string(item, "critical_user_journey", location, errors)
        tier = _required_string(item, "service_tier", location, errors)
        budget = _required_string(item, "error_budget", location, errors)
        tasks = _string_list(item, "tasks", location, errors)
        hints = _string_list(item, "hints", location, errors)

        sla = item.get("sla")
        if not isinstance(sla, dict) or not sla:
            errors.append(f"{location}.sla must be a non-empty mapping")
            sla = {}
        slos = item.get("slos")
        if not isinstance(slos, list) or not slos or not all(isinstance(entry, dict) and entry for entry in slos):
            errors.append(f"{location}.slos must be a non-empty list of mappings")
            slos = []
        slis = item.get("slis")
        if not isinstance(slis, list) or not slis or not all(isinstance(entry, dict) and entry for entry in slis):
            errors.append(f"{location}.slis must be a non-empty list of mappings")
            slis = []

        raw_faults = item.get("fault_profile")
        if not isinstance(raw_faults, list) or not raw_faults:
            errors.append(f"{location}.fault_profile must be a non-empty list")
            raw_faults = []
        faults: list[Fault] = []
        for fault_index, raw_fault in enumerate(raw_faults):
            fault_location = f"{location}.fault_profile[{fault_index}]"
            if not isinstance(raw_fault, dict):
                errors.append(f"{fault_location} must be a mapping")
                continue
            flag = _required_string(raw_fault, "flag", fault_location, errors)
            variant = _required_string(raw_fault, "variant", fault_location, errors)
            if flag and flag not in flags:
                errors.append(f"{fault_location}.flag references unknown flag {flag!r}")
            elif flag and variant and variant not in flags[flag].variants:
                errors.append(f"{fault_location}.variant {variant!r} is not allowed for {flag!r}")
            faults.append(Fault(flag, variant))

        observation_minutes = item.get("observation_minutes")
        if not isinstance(observation_minutes, int) or observation_minutes < 1:
            errors.append(f"{location}.observation_minutes must be a positive integer")
            observation_minutes = 1

        solution = item.get("solution")
        if not isinstance(solution, dict):
            errors.append(f"{location}.solution must be a mapping")
            solution = {}
        else:
            for key in ("root_cause", "investigation", "remediation", "learning_notes", "promql", "expected_evidence"):
                value = solution.get(key)
                if key in ("promql", "expected_evidence"):
                    if not isinstance(value, list) or not value or not all(isinstance(entry, str) and entry.strip() for entry in value):
                        errors.append(f"{location}.solution.{key} must be a non-empty list of strings")
                elif not isinstance(value, str) or not value.strip():
                    errors.append(f"{location}.solution.{key} must be a non-empty string")

        raw_rubric = item.get("rubric")
        if not isinstance(raw_rubric, list) or not raw_rubric:
            errors.append(f"{location}.rubric must be a non-empty list")
            raw_rubric = []
        rubric: list[dict[str, Any]] = []
        rubric_ids: list[str] = []
        total_points = 0
        for rubric_index, criterion in enumerate(raw_rubric):
            rubric_location = f"{location}.rubric[{rubric_index}]"
            if not isinstance(criterion, dict):
                errors.append(f"{rubric_location} must be a mapping")
                continue
            criterion_id = _required_string(criterion, "id", rubric_location, errors)
            text = _required_string(criterion, "criterion", rubric_location, errors)
            points = criterion.get("points")
            if not isinstance(points, int) or points < 1:
                errors.append(f"{rubric_location}.points must be a positive integer")
                points = 0
            rubric_ids.append(criterion_id)
            total_points += points
            rubric.append({"id": criterion_id, "criterion": text, "points": points})
        if len(rubric_ids) != len(set(rubric_ids)):
            errors.append(f"{location}.rubric IDs must be unique")
        if total_points != 100:
            errors.append(f"{location}.rubric points must total 100 (found {total_points})")

        if level and level not in level_ids:
            errors.append(f"{location}.level references unknown level {level!r}")
        scenarios.append(
            Scenario(
                scenario_id,
                level,
                scenario_title,
                concepts,
                briefing,
                journey,
                tier,
                sla,
                tuple(slos),
                tuple(slis),
                budget,
                tuple(faults),
                observation_minutes,
                tasks,
                hints,
                solution,
                tuple(rubric),
            )
        )

    scenario_ids = [scenario.id for scenario in scenarios]
    if len(scenario_ids) != len(set(scenario_ids)):
        errors.append("scenario IDs must be unique")
    if errors:
        raise BankValidationError(errors)
    return QuestionBank(schema_version, bank_id, title, description, tuple(sorted(levels, key=lambda level: level.order)), flags, tuple(scenarios))


def get_path(document: Any, path: tuple[str | int, ...]) -> Any:
    current = document
    for part in path:
        try:
            current = current[part]
        except (KeyError, IndexError, TypeError) as exc:
            raise KeyError(f"Missing path component {part!r} in {list(path)!r}") from exc
    return current


def set_path(document: Any, path: tuple[str | int, ...], value: Any) -> None:
    if not path:
        raise KeyError("Cannot replace the document root")
    parent = get_path(document, path[:-1])
    final = path[-1]
    try:
        parent[final] = value
    except (KeyError, IndexError, TypeError) as exc:
        raise KeyError(f"Cannot set path {list(path)!r}") from exc


def validate_bank_against_flags(bank: QuestionBank, document: dict[str, Any]) -> None:
    errors: list[str] = []
    live_flags = document.get("flags") if isinstance(document, dict) else None
    if not isinstance(live_flags, dict):
        raise BankValidationError(["The flag document must contain a flags mapping"])
    for flag_id, spec in bank.flags.items():
        try:
            current = get_path(document, spec.path)
        except KeyError as exc:
            errors.append(f"{flag_id}: {exc}")
            continue
        if current not in spec.variants:
            errors.append(f"{flag_id}: current value {current!r} is not declared in variants")
        live_spec = live_flags.get(flag_id)
        live_variants = live_spec.get("variants") if isinstance(live_spec, dict) else None
        if not isinstance(live_variants, dict):
            errors.append(f"{flag_id}: not present in the live flag catalog")
        else:
            missing = sorted(set(spec.variants) - set(live_variants))
            if missing:
                errors.append(f"{flag_id}: variants not present in the live flag document: {', '.join(missing)}")
    if errors:
        raise BankValidationError(errors)


def build_scenario_document(document: dict[str, Any], bank: QuestionBank, scenario: Scenario) -> dict[str, Any]:
    result = copy.deepcopy(document)
    for spec in bank.flags.values():
        set_path(result, spec.path, spec.safe_variant)
    for fault in scenario.fault_profile:
        set_path(result, bank.flags[fault.flag].path, fault.variant)
    return result


def choose_scenario(
    bank: QuestionBank,
    level_id: str,
    completed_ids: set[str],
    rng: random.Random | None = None,
) -> Scenario:
    candidates = bank.scenarios_for_level(level_id)
    if not candidates:
        raise ValueError(f"No scenarios exist for level {level_id!r}")
    incomplete = [scenario for scenario in candidates if scenario.id not in completed_ids]
    return (rng or random).choice(incomplete or candidates)


def score_rubric(rubric: tuple[dict[str, Any], ...], checked_ids: set[str]) -> int:
    return sum(int(item["points"]) for item in rubric if item["id"] in checked_ids)

