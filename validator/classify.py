"""Labels for one fixture: validity, repair, and the three error classes."""

from __future__ import annotations

from dataclasses import dataclass

from validator.model import Action, State
from validator.replay import replay
from validator.trace import Trace


@dataclass(frozen=True)
class Observation:
    fixture_id: str
    strict: Trace
    lenient: Trace
    alternative: Trace | None
    alternative_role: str | None
    plans_differ: bool

    @property
    def invalid_steps(self) -> tuple[int, ...]:
        return self.strict.invalid_steps

    @property
    def original_valid(self) -> bool:
        return self.strict.valid

    @property
    def alternative_valid(self) -> bool | None:
        if self.alternative is None:
            return None
        return self.alternative.valid

    @property
    def unnecessary_rewrite(self) -> bool:
        return self.alternative_role == "rewrite" and self.original_valid and self.plans_differ

    @property
    def masked_steps(self) -> tuple[int, ...]:
        """Steps the strict replay rejects and the lenient replay accepts.

        Those steps are an invalid continuation that stays hidden if a
        failed action is allowed to write its effects.
        """

        strict_invalid = set(self.strict.invalid_steps)
        lenient_invalid = set(self.lenient.invalid_steps)
        return tuple(sorted(strict_invalid - lenient_invalid))

    @property
    def blind_checker_would_accept(self) -> bool:
        """A checker that ignores preconditions accepts every plan."""

        return True


def observe(
    fixture_id: str,
    start: State,
    plan: tuple[Action, ...],
    alternative: tuple[Action, ...] | None,
    alternative_role: str | None,
) -> Observation:
    strict = replay(start, plan, apply_failed_effects=False)
    lenient = replay(start, plan, apply_failed_effects=True)
    alternative_trace = None
    plans_differ = False
    if alternative is not None:
        alternative_trace = replay(start, alternative, apply_failed_effects=False)
        plans_differ = [action.name for action in plan] != [action.name for action in alternative]
    return Observation(
        fixture_id=fixture_id,
        strict=strict,
        lenient=lenient,
        alternative=alternative_trace,
        alternative_role=alternative_role,
        plans_differ=plans_differ,
    )
