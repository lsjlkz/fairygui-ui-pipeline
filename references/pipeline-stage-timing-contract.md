# Pipeline Stage Timing Contract

Use this contract for every FairyGUI UI pipeline run. Timing is a required production artifact, not an estimate written from memory after the work is finished.

## Purpose

At the end of a pipeline run, the user must be able to see:

- how long every canonical stage took
- which stages were completed, skipped, blocked, or failed
- how much time was active processing
- how much time was spent waiting for human approval
- how much time belonged to external FairyGUI Editor or Unity work
- how much wall-clock time was not assigned to a stage
- how many attempts or rework passes each stage required

Do not infer durations from file modification times. Start and finish each stage explicitly.

## Required Reports

Every run writes:

```text
reports/pipeline_stage_timings.json
reports/pipeline_stage_timings.md
```

The JSON file is the machine-readable source of truth. The Markdown file is the human-readable summary that must be included in the final handoff.

## Canonical Stages

The report must contain all stages, even when some are skipped:

| Number | Stage ID | Stage Name | Default Category |
|---:|---|---|---|
| 1 | `requirement_intake` | Requirement intake | active |
| 2 | `ux_ui_spec` | UX/UI spec generation | active |
| 3 | `visual_design_brief` | Visual design brief | active |
| 4 | `design_mockup_generation` | Full-screen design mockup generation | active |
| 5 | `design_approval` | Explicit human design approval | waiting |
| 6 | `semantic_analysis` | Requirement-to-approved-design semantic analysis | active |
| 7 | `layout_analysis` | Approved-design-to-layout analysis | active |
| 8 | `asset_planning` | Asset and sheet planning | active |
| 9 | `resource_generation` | Production image generation | active |
| 10 | `sheet_slicing` | Sheet slicing | active |
| 11 | `fairygui_assembly` | FairyGUI assembly planning | active |
| 12 | `package_staging` | FairyGUI package resource staging | active |
| 13 | `xml_generation` | XML readiness and draft generation | active |
| 14 | `validation` | Pipeline and XML validation | active |
| 15 | `editor_publish` | FairyGUI editor review and publish | external |
| 16 | `unity_smoke_test` | Unity import and smoke test | external |

A project may add substages to notes or artifacts, but must not replace or rename the canonical stage IDs.

## Categories

- `active`: AI, script, image generation, document generation, slicing, XML generation, or validation work.
- `waiting`: elapsed time waiting for explicit user or human-review action. Stage 5 is normally waiting time.
- `external`: FairyGUI Editor, Unity, or another external application operated outside the automated pipeline.

The final report must show category totals separately. Do not report human waiting time as active production time.

## Status Values

Each stage and attempt uses one of:

- `pending`
- `running`
- `completed`
- `skipped`
- `blocked`
- `failed`

A completed full pipeline may contain only `completed` and `skipped` stages. A blocked, failed, or partial run must say so explicitly.

## Attempts And Rework

A stage may have multiple attempts. The stage duration is the sum of all attempts.

Examples:

- first design mockup attempt completed, user requested revisions, second attempt completed
- XML generation failed validation, XML was repaired, second XML-generation attempt completed
- design approval was blocked because the file hash changed, then a later approval attempt completed

Do not overwrite an earlier attempt. Preserve its status, timestamps, duration, note, and artifacts.

## Timing Semantics

All timestamps use UTC ISO 8601 with timezone information.

For each attempt:

```text
durationMs = finishedAt - startedAt
```

The pipeline summary includes:

- `wallClockDurationMs`: run finish/current time minus run start
- `activeDurationMs`: sum of active-stage attempts
- `waitingDurationMs`: sum of waiting-stage attempts
- `externalDurationMs`: sum of external-stage attempts
- `accountedDurationMs`: sum of all attempt durations
- `untrackedDurationMs`: wall-clock duration not assigned to a stage

Only one stage may be running at a time. This keeps category totals and untracked time meaningful. Do not overlap stages merely to reduce the reported total.

## Human Approval Wait

When a mockup is presented for approval:

1. finish `design_mockup_generation`
2. start `design_approval`
3. create/update `design_approval.json` as pending
4. stop the production pipeline
5. after explicit approval or rejection, finish `design_approval` with the corresponding status
6. continue or rework as appropriate

The waiting duration may span separate conversations or processes. Preserve the same timing JSON file.

## Required Commands

Initialize before Stage 1:

```bash
python scripts/record_pipeline_timing.py --root UIProduction init
```

Start a stage:

```bash
python scripts/record_pipeline_timing.py --root UIProduction start --stage requirement_intake
```

Finish a stage:

```bash
python scripts/record_pipeline_timing.py --root UIProduction finish --stage requirement_intake --status completed --artifact specs/ui_spec.md
```

Mark a non-applicable stage:

```bash
python scripts/record_pipeline_timing.py --root UIProduction skip --stage sheet_slicing --note "No sprite sheet was used."
```

Write an interim report without declaring completion:

```bash
python scripts/record_pipeline_timing.py --root UIProduction snapshot
```

Finalize the full pipeline:

```bash
python scripts/record_pipeline_timing.py --root UIProduction finalize --status completed
```

Validate the timing record:

```bash
python scripts/record_pipeline_timing.py --root UIProduction validate
```

## Command Wrapper

For command-driven stages, use the wrapper so failure status and duration are captured automatically:

```bash
python scripts/record_pipeline_timing.py --root UIProduction run --stage validation -- python scripts/validate_pipeline.py --root UIProduction
```

A zero exit code completes the stage. A non-zero exit code marks the attempt failed and is returned to the caller.

## Final Handoff Rule

Before saying that the pipeline is complete:

1. no stage may remain `running`
2. `finalize --status completed` must pass
3. `validate` must pass
4. both timing report files must exist
5. the final response must summarize total wall-clock, active, waiting, and external time and link or identify the two report files

If FairyGUI Editor or Unity work has not happened, mark those stages `pending` for a partial run or `skipped` only when they are genuinely outside the agreed scope. Do not mark the full pipeline completed while required external stages remain pending.
