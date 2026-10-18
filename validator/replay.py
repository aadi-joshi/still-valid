"""Replay an ordered plan under an explicit failure convention.

The convention, fixed before looking at outcomes:

1. Start from the initial state.
2. Apply the stated world-state change.
3. Walk the plan in order.
4. Record every unmet precondition.
5. If any precondition fails, do not apply that action's effects.
6. Keep walking, so a later step is judged against the state that
   actually resulted.

``apply_failed_effects=True`` is not the validator. It is the contrast
used to detect an invalid continuation: a later step that looks legal
only because a failed action was allowed to write its effects.
"""

from __future__ import annotations

from validator.model import Action, Literal, State
from validator.trace import StepRecord, Trace


def apply_change(state: State, change: tuple[Literal, ...]) -> State:
    return state.apply(change)


def replay(
    state: State,
    plan: tuple[Action, ...],
    *,
    apply_failed_effects: bool = False,
) -> Trace:
    current = state
    # Retained for the whole replay, including after a later successful write
    # of the same fact. See StepRecord.withheld_by.
    failed_producers: dict[tuple[str, bool], list[str]] = {}
    steps: list[StepRecord] = []

    for index, action in enumerate(plan, start=1):
        unmet = current.unmet(action.preconditions)
        applied = not unmet
        links: list[tuple[str, tuple[str, ...]]] = []
        if not applied:
            for literal in unmet:
                producers = failed_producers.get((literal.fact, literal.value), ())
                if producers:
                    links.append((literal.fact, tuple(producers)))
        if applied or apply_failed_effects:
            nxt = current.apply(action.effects)
        else:
            nxt = current
            for effect in action.effects:
                failed_producers.setdefault((effect.fact, effect.value), []).append(action.name)
        steps.append(
            StepRecord(
                index=index,
                action=action.name,
                state_before=current.snapshot(),
                unmet=unmet,
                applied=applied,
                state_after=nxt.snapshot(),
                withheld_by=tuple(links),
            )
        )
        current = nxt

    return Trace(tuple(steps))
