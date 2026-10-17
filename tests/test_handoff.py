"""Checks for the five-fixture handoff. Run from the repository root."""

from __future__ import annotations

import unittest

from validator.evaluate import build_report, distinction_errors, evaluate_fixture
from validator.load import REQUIRED_IDS, load_fixtures
from validator.replay import apply_change


class HandoffTest(unittest.TestCase):
    def test_command_passes(self) -> None:
        text, ok = build_report()
        self.assertTrue(ok, text)
        self.assertIn("RESULT: pass", text)
        for fixture_id in REQUIRED_IDS:
            self.assertIn(fixture_id, text)

    def test_five_fixtures_and_distinctions(self) -> None:
        fixtures = load_fixtures()
        self.assertEqual(tuple(fixture.id for fixture in fixtures), REQUIRED_IDS)
        rows = tuple(evaluate_fixture(fixture) for fixture in fixtures)
        self.assertEqual(distinction_errors(rows), [])
        for row in rows:
            self.assertEqual(row.mismatches, ())

    def test_case3_names_the_withheld_effect(self) -> None:
        fixture = next(item for item in load_fixtures() if item.id == "03_failed_effect_blocks_later_step")
        observation = evaluate_fixture(fixture).observation
        later = observation.strict.steps[1]
        self.assertEqual(later.unmet[0].fact, "cabinet_open")
        self.assertEqual(later.withheld_by, (("cabinet_open", ("unlock_cabinet",)),))
        self.assertEqual(observation.strict.steps[0].state_before["cabinet_open"], False)
        self.assertEqual(observation.strict.steps[0].state_after["cabinet_open"], False)

    def test_case4_no_repair_differs_from_repair(self) -> None:
        fixture = next(item for item in load_fixtures() if item.id == "04_reference_repair")
        observation = evaluate_fixture(fixture).observation
        self.assertFalse(observation.original_valid)
        self.assertTrue(observation.alternative_valid)
        self.assertEqual(observation.alternative_role, "repair")
        self.assertFalse(observation.unnecessary_rewrite)

    def test_change_is_visible_to_the_first_step(self) -> None:
        fixture = next(item for item in load_fixtures() if item.id == "02_resource_disappears")
        start = apply_change(fixture.initial, fixture.change)
        self.assertFalse(start.holds(fixture.plan[0].preconditions[0]))
        self.assertTrue(fixture.initial.holds(fixture.plan[0].preconditions[0]))


if __name__ == "__main__":
    unittest.main()
