# Plan validator

First component of a study on plan reliability after the world changes.

Question: when a deterministic world-state change invalidates an existing plan, can a validator identify the failing action preconditions and reject an invalid continuation while leaving a still-valid plan alone?

This repository answers that on five synthetic Boolean domains. It is a checker. It does not generate plans, call a model, or load a dataset. A larger implementation would be a separate step, after review of this one.

Requires Python 3.10 or newer. No third-party packages.

## Run

From the repository root:

```text
python -m validator
```

The command loads `fixtures/*.json`, applies each world-state change, replays the plan, and compares the result with the `expected` object in that file. It then runs 200 further replays from random seed 0. The same text is written to `results/expected_vs_observed.txt`.

Exit code 0 means every expected value matched. Exit code 1 means a mismatch or a failed property check. The `expected` blocks are the oracle. A failure is fixed in the checker, not by editing the oracle to match a wrong trace.

The same checks run under:

```text
python -m unittest discover -s tests -v
```

`python -m validator` is the handoff command.

## Replay rule

1. Start from the initial state. A missing fact is false.
2. Apply the stated change once, before any step. The change assigns one or more facts together.
3. Walk the ordered plan. Step numbers start at 1.
4. Record every precondition that does not hold.
5. If any precondition fails, do not apply that action's effects.
6. Keep walking. Later steps see the state that actually resulted.

A contrast replay applies effects even when preconditions fail. If that contrast accepts a step the strict replay rejects, the strict replay has refused an invalid continuation. The contrast is reported. It is not the validator.

## Five fixtures

| Fixture | Case |
| --- | --- |
| `01_unrelated_change` | `weather_clear` flips. The cabinet plan never reads it, so the original plan stays valid. |
| `02_resource_disappears` | `tool_ready` becomes false. `take_tool` fails. `read_gauge` does not use that tool and stays valid. |
| `03_failed_effect_blocks_later_step` | `have_key` becomes false. `unlock_cabinet` fails and does not open the cabinet. `power_panel` then fails because `cabinet_open` was withheld. |
| `04_reference_repair` | Same break as fixture 03. The original plan is the no-repair column. `fetch_spare_key`, then the original steps, replays cleanly. |
| `05_unnecessary_rewrite` | The weather flip again. The original plan is valid. Another plan inserts `log_status` and is also valid. That difference is an unnecessary rewrite. |

Three outcomes stay separate:

- Missed invalidation would be calling fixtures 02, 03, or 04 valid.
- Invalid continuation would be accepting `power_panel` in fixture 03 because the failed unlock was allowed to write `cabinet_open`.
- Unnecessary rewriting is fixture 05. The original plan is valid, so the new plan is not labelled as an invalid continuation.

The table's no-repair column is always the original plan after the change, before any supplied repair or rewrite.

## Layout

| Path | Contents |
| --- | --- |
| `validator/model.py` | Boolean state, literals, actions |
| `validator/trace.py` | Per-step record, including which failed action withheld a fact |
| `validator/replay.py` | Replay rule and the lenient contrast |
| `validator/classify.py` | Validity, repair, unnecessary rewrite, masked continuation |
| `validator/checks.py` | Comparison against the fixture oracle |
| `validator/load.py` | JSON fixtures |
| `validator/properties.py` | Seeded checks of the same rule |
| `validator/evaluate.py` | The one command and the table |
| `fixtures/` | The five labelled worlds |
| `docs/literature_review.md` | Background and references |
| `results/expected_vs_observed.txt` | Table from the last run |

## Limitations

- Facts are Boolean. There are no numbers, time, probabilities, or quantifiers over objects.
- The plan is one total order. Partial-order and temporal monitors are discussed in the literature note and not implemented.
- The change is applied once, before the first step. A disturbance between two steps is a different monitor.
- A failed step writes nothing. The lenient contrast makes that bookkeeping visible.
- "Valid" means every precondition held. The checker does not test an unstated goal. Fixture 04's repair does power the panel, and that is not a separate goal check.
- The repair and the rewrite are written in the fixtures. Nothing searches for them.
- An unnecessary rewrite is any different plan offered while the original plan still replays. The checker does not measure edit distance, and it does not prefer a cheaper plan.
- The random suite uses a fixed seed and small action sets. It guards the rule. It is not a planning benchmark.
- The run is local Boolean lookup. It does not need a GPU.

## Background

`docs/literature_review.md` places the replay rule against STRIPS and PLANEX, VAL, execution monitoring, plan repair and plan stability, and recent work that puts a symbolic checker in front of a language-model planner. Those papers are context. This repository does not rerun them.
