"""Loader rejects ambiguous fixture JSON. Expectations of the five fixtures stay as written."""

from __future__ import annotations

import json
import random
import tempfile
import unittest
from pathlib import Path

from validator.checks import compare
from validator.classify import observe
from validator.model import Action, State
from validator.replay import apply_change, replay
from validator.load import load_fixture


def _payload() -> dict:
    return {
        "id": "review_only",
        "title": "Reviewer synthetic fixture",
        "initial_state": {"key": False},
        "change": {},
        "actions": {"open": {"preconditions": {"key": True}, "effects": {"open": True}}},
        "plan": ["open"],
        "expected": {
            "invalid_steps": [1],
            "original_valid": False,
            "alternative_valid": None,
            "unnecessary_rewrite": False,
        },
    }


class LoaderTest(unittest.TestCase):
    def read(self, data: dict | str):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "fixture.json"
            text = data if isinstance(data, str) else json.dumps(data)
            path.write_text(text, encoding="utf-8")
            return load_fixture(path)

    def test_valid_integer_expectation_matches(self) -> None:
        fixture = self.read(_payload())
        observation = observe(
            fixture.id,
            apply_change(fixture.initial, fixture.change),
            fixture.plan,
            fixture.alternative,
            fixture.alternative_role,
        )
        self.assertEqual(compare(fixture.expectation, observation), [])

    def test_boolean_step_number_must_be_rejected(self) -> None:
        payload = _payload()
        payload["expected"]["invalid_steps"] = [True]
        with self.assertRaises(ValueError):
            self.read(payload)

    def test_duplicate_top_level_key_must_be_rejected(self) -> None:
        text = json.dumps(_payload())
        text = text[:-1] + ',"plan":[]}'
        with self.assertRaises(ValueError):
            self.read(text)

    def test_duplicate_fact_key_must_be_rejected(self) -> None:
        text = json.dumps(_payload()).replace('"key": false', '"key": true, "key": false', 1)
        with self.assertRaises(ValueError):
            self.read(text)

    def test_duplicate_nested_effect_key_must_be_rejected(self) -> None:
        text = json.dumps(_payload()).replace(
            '"open": true',
            '"open": true, "open": false',
            1,
        )
        with self.assertRaises(ValueError):
            self.read(text)

    def test_zero_step_number_rejected(self) -> None:
        payload = _payload()
        payload["expected"]["invalid_steps"] = [0]
        with self.assertRaises(ValueError):
            self.read(payload)

    def test_float_step_number_rejected(self) -> None:
        payload = _payload()
        payload["expected"]["invalid_steps"] = [1.5]
        with self.assertRaises(ValueError):
            self.read(payload)


class ReplayOracleTest(unittest.TestCase):
    def test_200_independent_oracle_replays(self) -> None:
        rng = random.Random(7421)
        facts = ("a", "b", "c")
        for case in range(200):
            initial = {fact: bool(rng.randrange(2)) for fact in facts}
            specs = []
            for step in range(rng.randrange(9)):
                preconditions = {fact: bool(rng.randrange(2)) for fact in facts if rng.random() < 0.45}
                effects = {fact: bool(rng.randrange(2)) for fact in facts if rng.random() < 0.45}
                specs.append((str(step), preconditions, effects))
            state = dict(initial)
            expected: list[int] = []
            snapshots = []
            for index, (_, preconditions, effects) in enumerate(specs, start=1):
                if all(state.get(fact, False) == value for fact, value in preconditions.items()):
                    state.update(effects)
                else:
                    expected.append(index)
                snapshots.append(dict(state))
            trace = replay(State(initial), tuple(Action.from_maps(*spec) for spec in specs))
            with self.subTest(case=case):
                self.assertEqual(trace.invalid_steps, tuple(expected))
                self.assertEqual([step.state_after for step in trace.steps], snapshots)


if __name__ == "__main__":
    unittest.main()
