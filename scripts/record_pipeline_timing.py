#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Record and report stage timing for the FairyGUI UI production pipeline."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

VERSION = "0.1.0"
PIPELINE_NAME = "fairygui-ui-pipeline"
CATEGORIES = {"active", "waiting", "external"}
ATTEMPT_FINAL_STATUSES = {"completed", "skipped", "blocked", "failed"}
PIPELINE_FINAL_STATUSES = {"completed", "blocked", "failed", "partial"}

CANONICAL_STAGES: tuple[tuple[int, str, str, str], ...] = (
    (1, "requirement_intake", "Requirement intake", "active"),
    (2, "ux_ui_spec", "UX/UI spec generation", "active"),
    (3, "visual_design_brief", "Visual design brief", "active"),
    (4, "design_mockup_generation", "Full-screen design mockup generation", "active"),
    (5, "design_approval", "Explicit human design approval", "waiting"),
    (6, "semantic_analysis", "Requirement-to-approved-design semantic analysis", "active"),
    (7, "layout_analysis", "Approved-design-to-layout analysis", "active"),
    (8, "asset_planning", "Asset and sheet planning", "active"),
    (9, "resource_generation", "Production image generation", "active"),
    (10, "sheet_slicing", "Sheet slicing", "active"),
    (11, "fairygui_assembly", "FairyGUI assembly planning", "active"),
    (12, "package_staging", "FairyGUI package resource staging", "active"),
    (13, "xml_generation", "XML readiness and draft generation", "active"),
    (14, "validation", "Pipeline and XML validation", "active"),
    (15, "editor_publish", "FairyGUI editor review and publish", "external"),
    (16, "unity_smoke_test", "Unity import and smoke test", "external"),
)
STAGE_IDS = {stage_id for _, stage_id, _, _ in CANONICAL_STAGES}


class TimingError(RuntimeError):
    """User-facing timing-state error."""


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def isoformat(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def parse_time(value: Any) -> datetime:
    if not isinstance(value, str) or not value:
        raise ValueError(f"invalid timestamp: {value!r}")
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def duration_ms(start: str, end: str) -> int:
    return max(0, round((parse_time(end) - parse_time(start)).total_seconds() * 1000))


def human_duration(milliseconds: int | None) -> str:
    if milliseconds is None:
        return "—"
    milliseconds = max(0, int(milliseconds))
    hours, remainder = divmod(milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    seconds, millis = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{millis:03d}"


def report_paths(root: Path) -> tuple[Path, Path]:
    reports = root / "reports"
    return reports / "pipeline_stage_timings.json", reports / "pipeline_stage_timings.md"


def initial_state(root: Path) -> dict[str, Any]:
    now = isoformat(utc_now())
    return {
        "version": VERSION,
        "runId": str(uuid.uuid4()),
        "pipeline": PIPELINE_NAME,
        "root": str(root.resolve()),
        "status": "running",
        "startedAt": now,
        "finishedAt": None,
        "updatedAt": now,
        "stages": [
            {
                "stageNumber": number,
                "stageId": stage_id,
                "name": name,
                "defaultCategory": category,
                "status": "pending",
                "attemptCount": 0,
                "durationMs": 0,
                "attempts": [],
            }
            for number, stage_id, name, category in CANONICAL_STAGES
        ],
        "summary": {},
    }


def load_state(root: Path) -> dict[str, Any]:
    json_path, _ = report_paths(root)
    if not json_path.is_file():
        raise TimingError(
            f"Timing record does not exist: {json_path}. Run the init command before Stage 1."
        )
    try:
        value = json.loads(json_path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        raise TimingError(f"Timing record cannot be read: {exc}") from exc
    if not isinstance(value, dict):
        raise TimingError("Timing record top-level value must be an object.")
    return value


def stage_by_id(state: dict[str, Any], stage_id: str) -> dict[str, Any]:
    for stage in state.get("stages", []):
        if isinstance(stage, dict) and stage.get("stageId") == stage_id:
            return stage
    raise TimingError(f"Unknown canonical stage: {stage_id}")


def all_attempts(state: dict[str, Any]) -> Iterable[tuple[dict[str, Any], dict[str, Any]]]:
    for stage in state.get("stages", []):
        if not isinstance(stage, dict):
            continue
        attempts = stage.get("attempts", [])
        if not isinstance(attempts, list):
            continue
        for attempt in attempts:
            if isinstance(attempt, dict):
                yield stage, attempt


def running_attempts(state: dict[str, Any]) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    return [
        (stage, attempt)
        for stage, attempt in all_attempts(state)
        if attempt.get("status") == "running"
    ]


def recompute(state: dict[str, Any], *, now: datetime | None = None) -> None:
    current = now or utc_now()
    category_totals = {category: 0 for category in CATEGORIES}
    status_counts = {
        "pending": 0,
        "running": 0,
        "completed": 0,
        "skipped": 0,
        "blocked": 0,
        "failed": 0,
    }
    accounted = 0

    for stage in state.get("stages", []):
        attempts = stage.get("attempts", []) if isinstance(stage, dict) else []
        total = 0
        latest_status = "pending"
        if isinstance(attempts, list) and attempts:
            latest_status = str(attempts[-1].get("status", "pending"))
            for attempt in attempts:
                if not isinstance(attempt, dict):
                    continue
                attempt_duration = attempt.get("durationMs")
                if attempt.get("status") == "running":
                    started_at = attempt.get("startedAt")
                    if isinstance(started_at, str):
                        attempt_duration = max(
                            0,
                            round((current - parse_time(started_at)).total_seconds() * 1000),
                        )
                if isinstance(attempt_duration, int) and attempt_duration >= 0:
                    total += attempt_duration
                    category = attempt.get("category", stage.get("defaultCategory"))
                    if category in category_totals:
                        category_totals[category] += attempt_duration
        stage["status"] = latest_status
        stage["attemptCount"] = len(attempts) if isinstance(attempts, list) else 0
        stage["durationMs"] = total
        status_counts[latest_status] = status_counts.get(latest_status, 0) + 1
        accounted += total

    run_start = parse_time(state["startedAt"])
    run_end = parse_time(state["finishedAt"]) if state.get("finishedAt") else current
    wall_clock = max(0, round((run_end - run_start).total_seconds() * 1000))
    untracked = max(0, wall_clock - accounted)

    state["summary"] = {
        "wallClockDurationMs": wall_clock,
        "activeDurationMs": category_totals["active"],
        "waitingDurationMs": category_totals["waiting"],
        "externalDurationMs": category_totals["external"],
        "accountedDurationMs": accounted,
        "untrackedDurationMs": untracked,
        "stageStatusCounts": status_counts,
        "human": {
            "wallClock": human_duration(wall_clock),
            "active": human_duration(category_totals["active"]),
            "waiting": human_duration(category_totals["waiting"]),
            "external": human_duration(category_totals["external"]),
            "accounted": human_duration(accounted),
            "untracked": human_duration(untracked),
        },
    }
    state["updatedAt"] = isoformat(current)


def atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp")
    temp.write_text(content, encoding="utf-8")
    temp.replace(path)


def markdown_escape(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def write_markdown(path: Path, state: dict[str, Any]) -> None:
    summary = state.get("summary", {})
    human = summary.get("human", {}) if isinstance(summary, dict) else {}
    lines = [
        "# Pipeline Stage Timing Report",
        "",
        f"- pipeline: `{state.get('pipeline', PIPELINE_NAME)}`",
        f"- run ID: `{state.get('runId', '')}`",
        f"- status: **{str(state.get('status', 'unknown')).upper()}**",
        f"- started: {state.get('startedAt', '')}",
        f"- finished: {state.get('finishedAt') or 'not finished'}",
        f"- total wall-clock: **{human.get('wallClock', '—')}**",
        f"- active processing: **{human.get('active', '—')}**",
        f"- human waiting: **{human.get('waiting', '—')}**",
        f"- external tools: **{human.get('external', '—')}**",
        f"- untracked/idle: **{human.get('untracked', '—')}**",
        "",
        "## Stage Summary",
        "",
        "| # | Stage | Category | Status | Attempts | Duration | Started | Finished |",
        "|---:|---|---|---|---:|---:|---|---|",
    ]

    for stage in state.get("stages", []):
        attempts = stage.get("attempts", []) if isinstance(stage, dict) else []
        first_start = "—"
        last_finish = "—"
        category = stage.get("defaultCategory", "active")
        if isinstance(attempts, list) and attempts:
            first_start = attempts[0].get("startedAt") or "—"
            last_finish = attempts[-1].get("finishedAt") or "running"
            used_categories = {
                attempt.get("category")
                for attempt in attempts
                if isinstance(attempt, dict) and attempt.get("category")
            }
            if len(used_categories) == 1:
                category = next(iter(used_categories))
            elif len(used_categories) > 1:
                category = "mixed"
        lines.append(
            "| {number} | `{stage_id}` — {name} | {category} | {status} | {attempts_count} | {duration} | {started} | {finished} |".format(
                number=stage.get("stageNumber", ""),
                stage_id=markdown_escape(stage.get("stageId", "")),
                name=markdown_escape(stage.get("name", "")),
                category=markdown_escape(category),
                status=markdown_escape(stage.get("status", "pending")),
                attempts_count=stage.get("attemptCount", 0),
                duration=human_duration(stage.get("durationMs", 0)),
                started=markdown_escape(first_start),
                finished=markdown_escape(last_finish),
            )
        )

    lines.extend(["", "## Attempts", ""])
    any_attempt = False
    for stage in state.get("stages", []):
        attempts = stage.get("attempts", []) if isinstance(stage, dict) else []
        if not isinstance(attempts, list) or not attempts:
            continue
        any_attempt = True
        lines.append(f"### {stage.get('stageNumber')}. `{stage.get('stageId')}`")
        lines.append("")
        for attempt in attempts:
            notes = attempt.get("notes", []) if isinstance(attempt, dict) else []
            artifacts = attempt.get("artifacts", []) if isinstance(attempt, dict) else []
            lines.append(
                f"- attempt {attempt.get('attempt')}: {attempt.get('status')} / "
                f"{attempt.get('category')} / {human_duration(attempt.get('durationMs'))} / "
                f"{attempt.get('startedAt')} → {attempt.get('finishedAt') or 'running'}"
            )
            for note in (notes if isinstance(notes, list) else []):
                lines.append(f"  - note: {note}")
            for artifact in (artifacts if isinstance(artifacts, list) else []):
                lines.append(f"  - artifact: `{artifact}`")
        lines.append("")
    if not any_attempt:
        lines.append("- no stage attempts recorded")
        lines.append("")

    lines.extend(
        [
            "## Accounting",
            "",
            f"- accounted duration: {human.get('accounted', '—')}",
            f"- untracked duration: {human.get('untracked', '—')}",
            "- timing uses UTC wall-clock timestamps; only one stage may run at a time.",
        ]
    )
    atomic_write(path, "\n".join(lines) + "\n")


def save_state(root: Path, state: dict[str, Any]) -> None:
    recompute(state)
    json_path, markdown_path = report_paths(root)
    atomic_write(json_path, json.dumps(state, ensure_ascii=False, indent=2) + "\n")
    write_markdown(markdown_path, state)


def append_unique(target: list[str], values: Iterable[str] | None) -> None:
    if values is None:
        return
    for value in values:
        cleaned = str(value).strip()
        if cleaned and cleaned not in target:
            target.append(cleaned)


def start_stage(
    state: dict[str, Any],
    stage_id: str,
    *,
    category: str | None,
    note: str | None,
    artifacts: Iterable[str] | None,
    rework: bool,
) -> dict[str, Any]:
    if state.get("status") == "completed":
        raise TimingError("A completed timing run cannot be resumed. Initialize a new run.")
    running = running_attempts(state)
    if running:
        active_stage = running[0][0].get("stageId")
        raise TimingError(f"Stage {active_stage} is already running. Finish it before starting {stage_id}.")

    stage = stage_by_id(state, stage_id)
    existing_attempts = stage.get("attempts", [])
    if isinstance(existing_attempts, list) and existing_attempts and not rework:
        raise TimingError(
            f"Stage {stage_id} already has {len(existing_attempts)} attempt(s). Use --rework to record another attempt."
        )
    selected_category = category or stage.get("defaultCategory")
    if selected_category not in CATEGORIES:
        raise TimingError(f"Invalid category: {selected_category}")

    now = isoformat(utc_now())
    attempts = stage.setdefault("attempts", [])
    attempt = {
        "attempt": len(attempts) + 1,
        "status": "running",
        "category": selected_category,
        "startedAt": now,
        "finishedAt": None,
        "durationMs": None,
        "notes": [],
        "artifacts": [],
    }
    if note:
        attempt["notes"].append(note)
    append_unique(attempt["artifacts"], artifacts)
    attempts.append(attempt)
    stage["status"] = "running"
    state["status"] = "running"
    state["finishedAt"] = None
    return attempt


def finish_stage(
    state: dict[str, Any],
    stage_id: str,
    *,
    status: str,
    note: str | None,
    artifacts: Iterable[str] | None,
) -> dict[str, Any]:
    if status not in ATTEMPT_FINAL_STATUSES - {"skipped"}:
        raise TimingError(f"Invalid finish status: {status}")
    stage = stage_by_id(state, stage_id)
    attempts = stage.get("attempts", [])
    if not isinstance(attempts, list) or not attempts or attempts[-1].get("status") != "running":
        raise TimingError(f"Stage {stage_id} has no running attempt to finish.")
    attempt = attempts[-1]
    now = isoformat(utc_now())
    attempt["finishedAt"] = now
    attempt["durationMs"] = duration_ms(attempt["startedAt"], now)
    attempt["status"] = status
    if note:
        attempt.setdefault("notes", []).append(note)
    append_unique(attempt.setdefault("artifacts", []), artifacts)
    stage["status"] = status
    if status in {"blocked", "failed"}:
        state["status"] = status
    else:
        state["status"] = "running"
    return attempt


def skip_stage(
    state: dict[str, Any],
    stage_id: str,
    *,
    note: str,
    artifacts: Iterable[str] | None,
    rework: bool,
) -> dict[str, Any]:
    if state.get("status") == "completed":
        raise TimingError("A completed timing run cannot be modified. Initialize a new run.")
    if running_attempts(state):
        raise TimingError("Finish the running stage before marking another stage skipped.")
    stage = stage_by_id(state, stage_id)
    existing_attempts = stage.get("attempts", [])
    if isinstance(existing_attempts, list) and existing_attempts and not rework:
        raise TimingError(
            f"Stage {stage_id} already has {len(existing_attempts)} attempt(s). Use --rework to append another attempt."
        )
    now = isoformat(utc_now())
    attempts = stage.setdefault("attempts", [])
    attempt = {
        "attempt": len(attempts) + 1,
        "status": "skipped",
        "category": stage.get("defaultCategory"),
        "startedAt": now,
        "finishedAt": now,
        "durationMs": 0,
        "notes": [note],
        "artifacts": [],
    }
    append_unique(attempt["artifacts"], artifacts)
    attempts.append(attempt)
    stage["status"] = "skipped"
    state["status"] = "running"
    state["finishedAt"] = None
    return attempt


def finalize(state: dict[str, Any], status: str) -> None:
    if status not in PIPELINE_FINAL_STATUSES:
        raise TimingError(f"Invalid pipeline status: {status}")
    running = running_attempts(state)
    if running:
        raise TimingError(
            "Cannot finalize while a stage is running: "
            + ", ".join(str(stage.get("stageId")) for stage, _ in running)
        )
    recompute(state)
    if status == "completed":
        invalid = [
            f"{stage.get('stageId')}={stage.get('status')}"
            for stage in state.get("stages", [])
            if stage.get("status") not in {"completed", "skipped"}
        ]
        if invalid:
            raise TimingError(
                "A completed pipeline requires every canonical stage to be completed or skipped: "
                + ", ".join(invalid)
            )
    state["status"] = status
    state["finishedAt"] = isoformat(utc_now())


def validate_state(state: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []

    if state.get("pipeline") != PIPELINE_NAME:
        errors.append(f"pipeline must be {PIPELINE_NAME}")
    if state.get("status") not in ({"running"} | PIPELINE_FINAL_STATUSES):
        errors.append(f"invalid pipeline status: {state.get('status')}")
    try:
        run_start = parse_time(state.get("startedAt"))
    except ValueError as exc:
        errors.append(str(exc))
        run_start = utc_now()
    finished_at = state.get("finishedAt")
    if finished_at:
        try:
            if parse_time(finished_at) < run_start:
                errors.append("finishedAt precedes startedAt")
        except ValueError as exc:
            errors.append(str(exc))

    stages = state.get("stages")
    if not isinstance(stages, list):
        errors.append("stages must be an array")
        stages = []
    actual_ids = [stage.get("stageId") for stage in stages if isinstance(stage, dict)]
    expected_ids = [stage_id for _, stage_id, _, _ in CANONICAL_STAGES]
    if actual_ids != expected_ids:
        errors.append("canonical stages are missing, duplicated, renamed, or out of order")

    intervals: list[tuple[datetime, datetime, str, int]] = []
    running_count = 0
    for stage in stages:
        if not isinstance(stage, dict):
            errors.append("stage entry must be an object")
            continue
        attempts = stage.get("attempts")
        if not isinstance(attempts, list):
            errors.append(f"{stage.get('stageId')}.attempts must be an array")
            continue
        for index, attempt in enumerate(attempts, start=1):
            if not isinstance(attempt, dict):
                errors.append(f"{stage.get('stageId')}.attempts[{index}] must be an object")
                continue
            if attempt.get("attempt") != index:
                errors.append(f"{stage.get('stageId')} attempt numbers are not contiguous")
            status = attempt.get("status")
            if status not in ({"running"} | ATTEMPT_FINAL_STATUSES):
                errors.append(f"{stage.get('stageId')} attempt {index} has invalid status {status}")
            if attempt.get("category") not in CATEGORIES:
                errors.append(f"{stage.get('stageId')} attempt {index} has invalid category")
            try:
                start = parse_time(attempt.get("startedAt"))
            except ValueError as exc:
                errors.append(f"{stage.get('stageId')} attempt {index}: {exc}")
                continue
            if status == "running":
                running_count += 1
                if attempt.get("finishedAt") is not None or attempt.get("durationMs") is not None:
                    errors.append(f"{stage.get('stageId')} running attempt must not have finish/duration")
                end = utc_now()
            else:
                try:
                    end = parse_time(attempt.get("finishedAt"))
                except ValueError as exc:
                    errors.append(f"{stage.get('stageId')} attempt {index}: {exc}")
                    continue
                expected = max(0, round((end - start).total_seconds() * 1000))
                actual = attempt.get("durationMs")
                if not isinstance(actual, int) or actual < 0:
                    errors.append(f"{stage.get('stageId')} attempt {index} has invalid durationMs")
                elif abs(actual - expected) > 5:
                    errors.append(
                        f"{stage.get('stageId')} attempt {index} duration mismatch: {actual} vs {expected}"
                    )
            if end < start:
                errors.append(f"{stage.get('stageId')} attempt {index} finishes before it starts")
            intervals.append((start, end, str(stage.get("stageId")), index))

    if running_count > 1:
        errors.append("more than one stage is running")
    intervals.sort(key=lambda item: item[0])
    for previous, current in zip(intervals, intervals[1:]):
        if current[0] < previous[1]:
            errors.append(
                f"stage attempts overlap: {previous[2]}#{previous[3]} and {current[2]}#{current[3]}"
            )

    if state.get("status") == "completed":
        invalid = [
            f"{stage.get('stageId')}={stage.get('status')}"
            for stage in stages
            if isinstance(stage, dict) and stage.get("status") not in {"completed", "skipped"}
        ]
        if invalid:
            errors.append("completed run contains non-final stages: " + ", ".join(invalid))
        if not state.get("finishedAt"):
            errors.append("completed run must have finishedAt")
    elif state.get("status") == "running" and state.get("finishedAt"):
        errors.append("running run must not have finishedAt")

    if state.get("status") in {"blocked", "failed", "partial"}:
        warnings.append("run is not a completed full pipeline")

    return {
        "ok": not errors,
        "runId": state.get("runId"),
        "status": state.get("status"),
        "errors": errors,
        "warnings": warnings,
    }


def action_result(root: Path, state: dict[str, Any], action: str, stage: str | None = None) -> str:
    json_path, markdown_path = report_paths(root)
    payload = {
        "ok": True,
        "action": action,
        "stage": stage,
        "status": state.get("status"),
        "runId": state.get("runId"),
        "jsonReport": str(json_path),
        "markdownReport": str(markdown_path),
        "summary": state.get("summary", {}),
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def add_common_stage_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--stage", required=True, choices=sorted(STAGE_IDS))
    parser.add_argument("--category", choices=sorted(CATEGORIES))
    parser.add_argument("--note")
    parser.add_argument("--artifact", action="append", default=[])
    parser.add_argument("--rework", action="store_true")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Record per-stage FairyGUI UI pipeline timing.")
    parser.add_argument("--root", type=Path, required=True, help="UIProduction root directory")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="Initialize a new timing run")
    init_parser.add_argument("--force", action="store_true", help="Replace an existing timing record")

    start_parser = subparsers.add_parser("start", help="Start a canonical pipeline stage")
    add_common_stage_arguments(start_parser)

    finish_parser = subparsers.add_parser("finish", help="Finish the currently running attempt of a stage")
    finish_parser.add_argument("--stage", required=True, choices=sorted(STAGE_IDS))
    finish_parser.add_argument("--status", choices=["completed", "blocked", "failed"], default="completed")
    finish_parser.add_argument("--note")
    finish_parser.add_argument("--artifact", action="append", default=[])

    skip_parser = subparsers.add_parser("skip", help="Mark a canonical stage as not applicable")
    skip_parser.add_argument("--stage", required=True, choices=sorted(STAGE_IDS))
    skip_parser.add_argument("--note", required=True)
    skip_parser.add_argument("--artifact", action="append", default=[])
    skip_parser.add_argument("--rework", action="store_true")

    subparsers.add_parser("snapshot", help="Refresh reports without finalizing the run")

    finalize_parser = subparsers.add_parser("finalize", help="Finalize a timing run")
    finalize_parser.add_argument("--status", choices=sorted(PIPELINE_FINAL_STATUSES), required=True)

    validate_parser = subparsers.add_parser("validate", help="Validate the timing record")
    validate_parser.add_argument("--out", type=Path)

    run_parser = subparsers.add_parser("run", help="Time a command as one pipeline stage")
    add_common_stage_arguments(run_parser)
    run_parser.add_argument(
        "command_args",
        nargs=argparse.REMAINDER,
        help="Command after --, for example: -- python scripts/validate_pipeline.py --root UIProduction",
    )

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    root = args.root.resolve()
    json_path, _ = report_paths(root)

    try:
        if args.command == "init":
            if json_path.exists() and not args.force:
                raise TimingError(
                    f"Timing record already exists: {json_path}. Use --force only when intentionally starting a new run."
                )
            state = initial_state(root)
            save_state(root, state)
            print(action_result(root, state, "init"))
            return 0

        state = load_state(root)

        if args.command == "start":
            start_stage(
                state,
                args.stage,
                category=args.category,
                note=args.note,
                artifacts=args.artifact,
                rework=args.rework,
            )
            save_state(root, state)
            print(action_result(root, state, "start", args.stage))
            return 0

        if args.command == "finish":
            finish_stage(
                state,
                args.stage,
                status=args.status,
                note=args.note,
                artifacts=args.artifact,
            )
            save_state(root, state)
            print(action_result(root, state, "finish", args.stage))
            return 0 if args.status == "completed" else 1

        if args.command == "skip":
            skip_stage(
                state,
                args.stage,
                note=args.note,
                artifacts=args.artifact,
                rework=args.rework,
            )
            save_state(root, state)
            print(action_result(root, state, "skip", args.stage))
            return 0

        if args.command == "snapshot":
            save_state(root, state)
            print(action_result(root, state, "snapshot"))
            return 0

        if args.command == "finalize":
            finalize(state, args.status)
            save_state(root, state)
            print(action_result(root, state, "finalize"))
            return 0 if args.status == "completed" else 1

        if args.command == "validate":
            recompute(state)
            validation = validate_state(state)
            output = json.dumps(validation, ensure_ascii=False, indent=2)
            if args.out:
                atomic_write(args.out.resolve(), output + "\n")
            print(output)
            return 0 if validation["ok"] else 1

        if args.command == "run":
            command_args = list(args.command_args)
            if command_args and command_args[0] == "--":
                command_args = command_args[1:]
            if not command_args:
                raise TimingError("The run command requires a child command after --.")
            start_stage(
                state,
                args.stage,
                category=args.category,
                note=args.note,
                artifacts=args.artifact,
                rework=args.rework,
            )
            save_state(root, state)
            try:
                completed = subprocess.run(command_args, check=False)
                return_code = int(completed.returncode)
                finish_stage(
                    state,
                    args.stage,
                    status="completed" if return_code == 0 else "failed",
                    note=f"command exit code: {return_code}",
                    artifacts=args.artifact,
                )
            except KeyboardInterrupt:
                finish_stage(
                    state,
                    args.stage,
                    status="failed",
                    note="command interrupted by user",
                    artifacts=args.artifact,
                )
                save_state(root, state)
                raise
            except OSError as exc:
                finish_stage(
                    state,
                    args.stage,
                    status="failed",
                    note=f"command could not start: {exc}",
                    artifacts=args.artifact,
                )
                save_state(root, state)
                raise TimingError(f"Child command could not start: {exc}") from exc
            save_state(root, state)
            print(action_result(root, state, "run", args.stage))
            return return_code

        raise TimingError(f"Unsupported command: {args.command}")

    except TimingError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False, indent=2), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
