"""Load the five labelled fixtures from JSON."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from validator.checks import Expectation
from validator.model import Action, Literal, State, literals_from_map

FIXTURE_DIR = Path(__file__).resolve().parent.parent / "fixtures"

REQUIRED_IDS = (
    "01_unrelated_change",
    "02_resource_disappears",
    "03_failed_effect_blocks_later_step",
    "04_reference_repair",
    "05_unnecessary_rewrite",
)


@dataclass(frozen=True)
class Fixture:
    id: str
    title: str
    initial: State
    change: tuple[Literal, ...]
    plan: tuple[Action, ...]
    alternative: tuple[Action, ...] | None
    alternative_role: str | None
    expectation: Expectation


def _require_map(payload: dict[str, Any], key: str, fixture_id: str) -> dict[str, Any]:
    value = payload.get(key)
    if not isinstance(value, dict):
        raise ValueError(f"{fixture_id}: '{key}' must be an object")
    return value


def _actions(payload: dict[str, Any], fixture_id: str) -> dict[str, Action]:
    raw = _require_map(payload, "actions", fixture_id)
    actions: dict[str, Action] = {}
    for name, spec in raw.items():
        if not isinstance(spec, dict):
            raise ValueError(f"{fixture_id}: action {name} must be an object")
        preconditions = spec.get("preconditions", {})
        effects = spec.get("effects", {})
        if not isinstance(preconditions, dict) or not isinstance(effects, dict):
            raise ValueError(f"{fixture_id}: action {name} preconditions and effects must be objects")
        actions[name] = Action.from_maps(name, preconditions, effects)
    return actions


def _plan(names: Any, actions: dict[str, Action], fixture_id: str, field: str) -> tuple[Action, ...]:
    if not isinstance(names, list) or any(not isinstance(name, str) for name in names):
        raise ValueError(f"{fixture_id}: '{field}' must be a list of action names")
    missing = [name for name in names if name not in actions]
    if missing:
        raise ValueError(f"{fixture_id}: {field} names unknown actions {missing}")
    return tuple(actions[name] for name in names)


def _json_int(step: Any) -> bool:
    """True only for a JSON integer.

    ``bool`` is a subclass of ``int``, and ``True == 1``, so
    ``isinstance(True, int)`` would accept a JSON ``true`` as step 1.
    """

    return type(step) is int


def _expectation(payload: dict[str, Any], fixture_id: str) -> Expectation:
    raw = _require_map(payload, "expected", fixture_id)
    invalid = raw.get("invalid_steps")
    if not isinstance(invalid, list) or any(not _json_int(step) or step < 1 for step in invalid):
        raise ValueError(f"{fixture_id}: expected.invalid_steps must be a list of 1-based step numbers")
    original_valid = raw.get("original_valid")
    alternative_valid = raw.get("alternative_valid")
    unnecessary = raw.get("unnecessary_rewrite")
    if not isinstance(original_valid, bool) or not isinstance(unnecessary, bool):
        raise ValueError(f"{fixture_id}: expected validity flags must be booleans")
    if alternative_valid is not None and not isinstance(alternative_valid, bool):
        raise ValueError(f"{fixture_id}: expected.alternative_valid must be true, false, or null")
    return Expectation(
        invalid_steps=tuple(invalid),
        original_valid=original_valid,
        alternative_valid=alternative_valid,
        unnecessary_rewrite=unnecessary,
    )


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    """Reject a repeated key instead of keeping the last value.

    RFC 8259 says object names should be unique. The default ``json.loads``
    keeps the last occurrence, which can change which plan or fact a fixture
    means. The hook runs for every object, so nested action maps are covered.
    """

    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON object key: {key!r}")
        result[key] = value
    return result


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_unique_object)
    except ValueError as exc:
        if str(exc).startswith("duplicate JSON object key:"):
            raise ValueError(f"{path.name}: {exc}") from exc
        raise


def load_fixture(path: Path) -> Fixture:
    payload = _load_json(path)
    if not isinstance(payload, dict):
        raise ValueError(f"{path.name}: fixture must be an object")
    fixture_id = payload.get("id")
    title = payload.get("title")
    if not isinstance(fixture_id, str) or not isinstance(title, str):
        raise ValueError(f"{path.name}: id and title must be strings")
    initial_raw = _require_map(payload, "initial_state", fixture_id)
    change_raw = _require_map(payload, "change", fixture_id)
    actions = _actions(payload, fixture_id)
    plan = _plan(payload.get("plan"), actions, fixture_id, "plan")
    alternative_raw = payload.get("alternative")
    alternative: tuple[Action, ...] | None = None
    role: str | None = None
    if alternative_raw is not None:
        if not isinstance(alternative_raw, dict):
            raise ValueError(f"{fixture_id}: alternative must be an object or null")
        role = alternative_raw.get("role")
        if role not in ("repair", "rewrite"):
            raise ValueError(f"{fixture_id}: alternative.role must be 'repair' or 'rewrite'")
        alternative = _plan(alternative_raw.get("plan"), actions, fixture_id, "alternative.plan")
    return Fixture(
        id=fixture_id,
        title=title,
        initial=State({str(fact): value for fact, value in initial_raw.items()}),
        change=literals_from_map({str(fact): value for fact, value in change_raw.items()}),
        plan=plan,
        alternative=alternative,
        alternative_role=role,
        expectation=_expectation(payload, fixture_id),
    )


def load_fixtures(directory: Path = FIXTURE_DIR) -> tuple[Fixture, ...]:
    paths = sorted(directory.glob("*.json"))
    fixtures = tuple(load_fixture(path) for path in paths)
    found = tuple(fixture.id for fixture in fixtures)
    if found != REQUIRED_IDS:
        raise ValueError(f"expected fixture ids {REQUIRED_IDS}, found {found}")
    return fixtures
