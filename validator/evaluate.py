"""One deterministic command for the five-fixture handoff."""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path

from validator.checks import compare
from validator.classify import Observation, observe
from validator.load import Fixture, load_fixtures
from validator.properties import run_property_checks
from validator.replay import apply_change
from validator.trace import Trace

RESULT_PATH = Path(__file__).resolve().parent.parent / "results" / "expected_vs_observed.txt"
PROPERTY_TRIALS = 200
PROPERTY_SEED = 0


@dataclass(frozen=True)
class Row:
    fixture: Fixture
    observation: Observation
    mismatches: tuple[str, ...]

    @property
    def matched(self) -> bool:
        return not self.mismatches


def _steps(steps: tuple[int, ...]) -> str:
    if not steps:
        return "none"
    return ",".join(str(step) for step in steps)


def _yes_no(value: bool | None) -> str:
    if value is None:
        return "n/a"
    return "yes" if value else "no"


def evaluate_fixture(fixture: Fixture) -> Row:
    start = apply_change(fixture.initial, fixture.change)
    observation = observe(
        fixture.id,
        start,
        fixture.plan,
        fixture.alternative,
        fixture.alternative_role,
    )
    mismatches = tuple(compare(fixture.expectation, observation))
    return Row(fixture, observation, mismatches)


def distinction_errors(rows: tuple[Row, ...]) -> list[str]:
    """The five fixtures have to exhibit the three error classes, not only match a table."""

    by_id = {row.fixture.id: row.observation for row in rows}
    errors: list[str] = []

    unrelated = by_id["01_unrelated_change"]
    if not unrelated.original_valid or unrelated.alternative is not None:
        errors.append("case 1 must leave the original plan valid and must not supply a rewrite")

    resource = by_id["02_resource_disappears"]
    if resource.invalid_steps != (1,) or resource.strict.steps[0].withheld_by:
        errors.append("case 2 must reject only the action whose resource disappeared")
    if len(resource.strict.steps) != 2 or not resource.strict.steps[1].applied:
        errors.append("case 2 must keep the independent later step valid")

    cascade = by_id["03_failed_effect_blocks_later_step"]
    if cascade.invalid_steps != (1, 2) or cascade.masked_steps != (2,):
        errors.append("case 3 must reject the later step only because the failed effect was withheld")
    if not cascade.strict.steps[1].withheld_by:
        errors.append("case 3 must name the failed action that withheld the later precondition")

    repair = by_id["04_reference_repair"]
    if repair.original_valid or repair.alternative_valid is not True or repair.unnecessary_rewrite:
        errors.append("case 4 must keep the no-repair plan invalid and accept the supplied repair")

    rewrite = by_id["05_unnecessary_rewrite"]
    if not (rewrite.unnecessary_rewrite and rewrite.original_valid and not rewrite.masked_steps):
        errors.append("case 5 must record a rewrite of a still-valid plan, separate from invalid continuation")
    if rewrite.alternative_valid is not True:
        errors.append("case 5 rewrite must itself be a legal plan, so the only fault is that it was unnecessary")

    invalid_cases = (resource, cascade, repair)
    if not all(case.blind_checker_would_accept and not case.original_valid for case in invalid_cases):
        errors.append("missed invalidation is not demonstrated: an invalid plan was not both rejected and blind-acceptable")

    return errors


def _trace_lines(title: str, observation: Observation) -> list[str]:
    lines = [f"TRACE {title}"]
    lines.extend(_one_trace("original", observation.strict))
    if observation.lenient.invalid_steps != observation.strict.invalid_steps:
        lines.append(
            "  lenient contrast invalid steps: "
            + _steps(observation.lenient.invalid_steps)
            + " (failed effects were applied; this is not the validator)"
        )
    if observation.alternative is not None:
        lines.extend(_one_trace(observation.alternative_role or "alternative", observation.alternative))
    return lines


def _one_trace(label: str, trace: Trace) -> list[str]:
    lines = [f"  {label}:"]
    if not trace.steps:
        lines.append("    (empty plan)")
        return lines
    for step in trace.steps:
        unmet = ", ".join(str(literal) for literal in step.unmet) if step.unmet else "none"
        withheld = ""
        if step.withheld_by:
            parts = [f"{fact} withheld by {', '.join(names)}" for fact, names in step.withheld_by]
            withheld = " [" + "; ".join(parts) + "]"
        status = "applied" if step.applied else "rejected"
        lines.append(f"    step {step.index} {step.action}: unmet {unmet}; {status}{withheld}")
    return lines


def render(rows: tuple[Row, ...], property_errors: list[str], elapsed_ms: float) -> str:
    headers = (
        "fixture",
        "expected_invalid",
        "observed_invalid",
        "match",
        "no_repair_valid",
        "alternative",
        "expected_alt_valid",
        "observed_alt_valid",
        "unnecessary_rewrite",
    )
    body = []
    for row in rows:
        observed = row.observation
        expected = row.fixture.expectation
        body.append(
            (
                row.fixture.id,
                _steps(expected.invalid_steps),
                _steps(observed.invalid_steps),
                "yes" if row.matched else "NO",
                _yes_no(observed.original_valid),
                observed.alternative_role or "n/a",
                _yes_no(expected.alternative_valid),
                _yes_no(observed.alternative_valid),
                _yes_no(observed.unnecessary_rewrite),
            )
        )
    widths = [len(header) for header in headers]
    for record in body:
        for index, cell in enumerate(record):
            widths[index] = max(widths[index], len(cell))

    def format_row(cells: tuple[str, ...]) -> str:
        return "  ".join(cell.ljust(widths[index]) for index, cell in enumerate(cells))

    lines = [
        "Plan validator: five synthetic fixtures",
        "Replay rule: apply the state change, then walk the plan in order.",
        "A step with any unmet precondition does not apply its effects.",
        "Later steps are checked against that state. Step numbers start at 1.",
        "",
        format_row(headers),
        format_row(tuple("-" * width for width in widths)),
    ]
    lines.extend(format_row(record) for record in body)
    lines.append("")
    lines.append("No-repair column is the original plan after the change, before any supplied repair or rewrite.")
    lines.append("")
    for row in rows:
        lines.append(row.fixture.title)
        lines.extend(_trace_lines(row.fixture.id, row.observation))
        if row.mismatches:
            lines.extend(f"  MISMATCH {item}" for item in row.mismatches)
        lines.append("")

    lines.append("Error classes")
    lines.append("  missed invalidation: fixtures 02, 03, and 04 are rejected at the unmet steps.")
    lines.append("    A checker that did not read preconditions would accept every sequence, including these.")
    lines.append("    This validator records the unmet steps instead.")
    lines.append("  invalid continuation: fixture 03 stays invalid at step 2 because unlock_cabinet did not")
    lines.append("    write cabinet_open. The lenient contrast applies that failed effect and then hides step 2.")
    lines.append("    The validator uses the strict rule and rejects the continuation.")
    lines.append("  unnecessary rewriting: fixture 05's original plan is valid. The other plan is recorded as a")
    lines.append("    rewrite, and it is not labelled as an invalid continuation.")
    lines.append("")
    if property_errors:
        lines.append(f"Property checks: FAIL ({PROPERTY_TRIALS} trials, seed {PROPERTY_SEED})")
        lines.extend(f"  {item}" for item in property_errors)
    else:
        lines.append(
            f"Property checks: pass ({PROPERTY_TRIALS} random replays, seed {PROPERTY_SEED}, "
            "plus the fixed cascade, change-order, empty-plan, and negative-precondition checks)"
        )
    lines.append(f"Elapsed: {elapsed_ms:.2f} ms")
    lines.append("Compute: local CPython, Boolean replay only. No GPU, model call, dataset, or remote run.")
    failed = any(not row.matched for row in rows) or bool(property_errors)
    lines.append("RESULT: FAIL" if failed else "RESULT: pass")
    return "\n".join(lines) + "\n"


def build_report() -> tuple[str, bool]:
    started = time.perf_counter()
    rows = tuple(evaluate_fixture(fixture) for fixture in load_fixtures())
    mismatches = [item for row in rows for item in row.mismatches]
    mismatches.extend(distinction_errors(rows))
    property_errors = run_property_checks(PROPERTY_TRIALS, PROPERTY_SEED)
    elapsed_ms = (time.perf_counter() - started) * 1000
    text = render(rows, property_errors, elapsed_ms)
    if mismatches:
        text = text.rstrip() + "\n\nCheck failures:\n" + "\n".join(f"  {item}" for item in mismatches) + "\n"
        # render already printed RESULT from row/property errors only.
        # Rebuild the last line if distinction checks failed while rows matched.
        if all(row.matched for row in rows) and not property_errors:
            text = text.replace("RESULT: pass", "RESULT: FAIL")
    ok = all(row.matched for row in rows) and not property_errors and not mismatches
    return text, ok


def main() -> int:
    text, ok = build_report()
    RESULT_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESULT_PATH.write_text(text, encoding="utf-8")
    print(text, end="")
    return 0 if ok else 1
