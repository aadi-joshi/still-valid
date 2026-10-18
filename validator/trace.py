"""Validation trace for one replay of an ordered plan."""

from __future__ import annotations

from dataclasses import dataclass

from validator.model import Literal


@dataclass(frozen=True)
class StepRecord:
    """One plan step after the world-state change has already been applied.

    ``withheld_by`` names earlier failed actions whose effects included an
    unmet literal. It is not dropped when a later successful action writes
    that fact, so after a still later deletion it can name a failed action
    that no longer explains the current state. Plan validity does not use
    this field. An empty tuple means no earlier failed action listed the
    literal, which is how a direct resource loss is distinguished from a
    cascade inside the current trace.
    """

    index: int
    action: str
    state_before: dict[str, bool]
    unmet: tuple[Literal, ...]
    applied: bool
    state_after: dict[str, bool]
    withheld_by: tuple[tuple[str, tuple[str, ...]], ...]

    @property
    def invalid(self) -> bool:
        return not self.applied


@dataclass(frozen=True)
class Trace:
    steps: tuple[StepRecord, ...]

    @property
    def invalid_steps(self) -> tuple[int, ...]:
        return tuple(step.index for step in self.steps if step.invalid)

    @property
    def valid(self) -> bool:
        return not self.invalid_steps
