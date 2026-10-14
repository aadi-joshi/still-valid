"""State and action interface.

A state is a closed-world assignment of Boolean facts: a fact that is
absent is false. An action names the literals that must hold before it
runs and the literals it writes if it runs.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class Literal:
    """One Boolean fact, required or produced at a specific value."""

    fact: str
    value: bool

    def __str__(self) -> str:
        return f"{self.fact}={str(self.value).lower()}"


def literals_from_map(mapping: Mapping[str, bool]) -> tuple[Literal, ...]:
    if any(not isinstance(value, bool) for value in mapping.values()):
        raise ValueError("fact values must be JSON booleans")
    return tuple(Literal(fact, mapping[fact]) for fact in sorted(mapping))


@dataclass(frozen=True)
class Action:
    name: str
    preconditions: tuple[Literal, ...]
    effects: tuple[Literal, ...]

    @staticmethod
    def from_maps(
        name: str,
        preconditions: Mapping[str, bool],
        effects: Mapping[str, bool],
    ) -> Action:
        if not isinstance(name, str) or not name:
            raise ValueError("action name must be a non-empty string")
        return Action(
            name,
            literals_from_map(preconditions),
            literals_from_map(effects),
        )


@dataclass(frozen=True)
class State:
    """Closed-world Boolean state. Missing facts are false."""

    values: Mapping[str, bool]

    def __post_init__(self) -> None:
        if any(not isinstance(value, bool) for value in self.values.values()):
            raise ValueError("state values must be booleans")
        object.__setattr__(self, "values", {fact: self.values[fact] for fact in sorted(self.values)})

    def holds(self, literal: Literal) -> bool:
        return self.values.get(literal.fact, False) == literal.value

    def unmet(self, preconditions: tuple[Literal, ...]) -> tuple[Literal, ...]:
        return tuple(literal for literal in preconditions if not self.holds(literal))

    def apply(self, effects: tuple[Literal, ...]) -> State:
        updated = dict(self.values)
        for literal in effects:
            updated[literal.fact] = literal.value
        return State(updated)

    def snapshot(self) -> dict[str, bool]:
        return dict(self.values)
