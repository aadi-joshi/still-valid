"""Expected-output checks.

The expected fields are written in the fixtures. They are not computed
by the replay function. A mismatch is a failed check, not a cue to
change the expectation.
"""

from __future__ import annotations

from dataclasses import dataclass

from validator.classify import Observation


@dataclass(frozen=True)
class Expectation:
    invalid_steps: tuple[int, ...]
    original_valid: bool
    alternative_valid: bool | None
    unnecessary_rewrite: bool


def compare(expectation: Expectation, observation: Observation) -> list[str]:
    """Return human-readable mismatches. An empty list means agreement."""

    errors: list[str] = []
    label = observation.fixture_id

    if expectation.original_valid != (len(expectation.invalid_steps) == 0):
        errors.append(
            f"{label}: expected original_valid={expectation.original_valid} "
            f"disagrees with expected invalid steps {list(expectation.invalid_steps)}"
        )
    if expectation.unnecessary_rewrite and not expectation.original_valid:
        errors.append(f"{label}: an unnecessary rewrite requires a still-valid original plan")

    if list(expectation.invalid_steps) != list(observation.invalid_steps):
        errors.append(
            f"{label}: invalid steps expected {list(expectation.invalid_steps)} "
            f"observed {list(observation.invalid_steps)}"
        )
    if expectation.original_valid != observation.original_valid:
        errors.append(
            f"{label}: original valid expected {expectation.original_valid} "
            f"observed {observation.original_valid}"
        )
    if expectation.alternative_valid != observation.alternative_valid:
        errors.append(
            f"{label}: alternative valid expected {expectation.alternative_valid} "
            f"observed {observation.alternative_valid}"
        )
    if expectation.unnecessary_rewrite != observation.unnecessary_rewrite:
        errors.append(
            f"{label}: unnecessary rewrite expected {expectation.unnecessary_rewrite} "
            f"observed {observation.unnecessary_rewrite}"
        )
    return errors
