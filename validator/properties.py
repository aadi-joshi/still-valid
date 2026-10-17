"""Seeded checks of the replay rule beyond the five fixtures.

The seed is fixed, so this suite is part of the one deterministic
command. It does not train anything and it does not call a model.
"""

from __future__ import annotations

import random

from validator.model import Action, Literal, State
from validator.replay import apply_change, replay


def _random_literals(rng: random.Random, facts: list[str]) -> dict[str, bool]:
    chosen = rng.sample(facts, rng.randint(0, len(facts)))
    return {fact: bool(rng.choice((True, False))) for fact in chosen}


def _fixed_checks() -> list[str]:
    errors: list[str] = []

    empty = replay(State({"only": True}), ())
    if not empty.valid or empty.steps:
        errors.append("empty plan must be valid and produce an empty trace")

    changed = apply_change(State({"have_key": True, "door_open": False}), (Literal("have_key", False),))
    blocked = replay(changed, (Action.from_maps("unlock", {"have_key": True}, {"door_open": True}),))
    if blocked.valid:
        errors.append("a change that removes a precondition must be applied before replay")
    if blocked.steps[0].state_after != blocked.steps[0].state_before:
        errors.append("a failed step must not write its effects")

    cascade_state = State({"ready": False, "done": False, "finished": False})
    cascade_plan = (
        Action.from_maps("first", {"ready": True}, {"done": True}),
        Action.from_maps("second", {"done": True}, {"finished": True}),
    )
    strict = replay(cascade_state, cascade_plan)
    lenient = replay(cascade_state, cascade_plan, apply_failed_effects=True)
    if strict.invalid_steps != (1, 2):
        errors.append(f"cascade strict invalid steps {strict.invalid_steps}, expected (1, 2)")
    if lenient.invalid_steps != (1,):
        errors.append(f"cascade lenient invalid steps {lenient.invalid_steps}, expected (1,)")
    withheld = strict.steps[1].withheld_by
    if not withheld or withheld[0] != ("done", ("first",)):
        errors.append(f"cascade withheld link {withheld}, expected done from first")

    negative = replay(
        State({"hatch_shut": True}),
        (Action.from_maps("open_hatch", {"hatch_shut": False}, {"hatch_shut": False}),),
    )
    if negative.valid:
        errors.append("a precondition that requires false must fail when the fact is true")

    return errors


def _trial(rng: random.Random, trial: int) -> list[str]:
    facts = [f"f{index}" for index in range(rng.randint(2, 5))]
    state = State({fact: bool(rng.choice((True, False))) for fact in facts})
    plan = tuple(
        Action.from_maps(f"a{index}", _random_literals(rng, facts), _random_literals(rng, facts))
        for index in range(rng.randint(0, 6))
    )
    strict = replay(state, plan)
    if strict != replay(state, plan):
        return [f"trial {trial}: replay was not deterministic"]

    loose = replay(state, plan, apply_failed_effects=True)
    seen_failure = False
    for step, action, loose_step in zip(strict.steps, plan, loose.steps):
        before = State(step.state_before)
        unmet = before.unmet(action.preconditions)
        if unmet != step.unmet or step.applied is not (not unmet):
            return [f"trial {trial}: unmet preconditions were recorded incorrectly"]
        if step.applied:
            expected_after = before.apply(action.effects).snapshot()
            if step.state_after != expected_after:
                return [f"trial {trial}: a successful step did not apply its effects"]
            if not seen_failure and loose_step.state_after != expected_after:
                return [f"trial {trial}: lenient replay diverged before the first failure"]
        else:
            if step.state_after != step.state_before:
                return [f"trial {trial}: a failed step applied its effects"]
            seen_failure = True
    return []


def run_property_checks(trials: int = 200, seed: int = 0) -> list[str]:
    errors = _fixed_checks()
    rng = random.Random(seed)
    for trial in range(trials):
        errors.extend(_trial(rng, trial))
        if errors:
            break
    return errors
