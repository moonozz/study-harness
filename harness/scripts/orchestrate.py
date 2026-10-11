#!/usr/bin/env python3
"""Create and advance deterministic design-harness runs."""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parents[2]
RUNS_ROOT = Path(os.environ.get("HARNESS_RUNS_ROOT", ROOT / "runs")).resolve()
DEFAULTS_PATH = ROOT / "harness" / "defaults.yaml"
TEMPLATES = ROOT / "harness" / "templates"
VALIDATOR = ROOT / "harness" / "scripts" / "validate.py"


def load_json(path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


DEFAULTS = load_json(DEFAULTS_PATH)


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def now_iso():
    return datetime.now(ZoneInfo("Asia/Seoul")).isoformat(timespec="seconds")


def safe_slug(value):
    slug = re.sub(r"[^0-9A-Za-z가-힣._-]+", "-", value.strip()).strip("-.")
    if not slug:
        raise ValueError("작업명에서 run-id를 만들 수 없습니다.")
    return slug


def resolve_run(run_id):
    run_dir = (RUNS_ROOT / run_id).resolve()
    if run_dir.parent != RUNS_ROOT or not run_dir.is_dir():
        raise ValueError("실행 폴더를 찾을 수 없습니다: {}".format(run_id))
    return run_dir


def state_path(run_dir):
    return run_dir / DEFAULTS["state_file"]


def load_state(run_dir):
    return load_json(state_path(run_dir))


def save_state(run_dir, state):
    state["updated_at"] = now_iso()
    write_json(state_path(run_dir), state)


def set_active(run_id, role):
    write_json(RUNS_ROOT / DEFAULTS["active_run_file"], {"run_id": run_id, "role": role, "updated_at": now_iso()})


def stage_role(stage):
    return DEFAULTS["stage_roles"][str(stage)]


def command_start(args):
    if not args.reference:
        raise ValueError("레퍼런스는 1개 이상 필요합니다.")
    if not 2 <= len(args.screen) <= 3:
        raise ValueError("대상 화면은 2~3개여야 합니다.")

    stamp = datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y%m%d-%H%M")
    run_id = "{}-{}".format(stamp, safe_slug(args.name))
    run_dir = RUNS_ROOT / run_id
    if run_dir.exists():
        raise ValueError("같은 run-id가 이미 존재합니다: {}".format(run_id))

    for relative in ("agents/research", "agents/screen", "agents/design"):
        (run_dir / relative).mkdir(parents=True, exist_ok=True)

    template_targets = {
        "01-reference-analysis.md": run_dir / DEFAULTS["stage_sources"]["1"],
        "02-screen-spec.md": run_dir / DEFAULTS["stage_sources"]["2"],
        "03-key-screens.md": run_dir / DEFAULTS["stage_sources"]["3"],
        "04-design-output.md": run_dir / DEFAULTS["stage_sources"]["4"],
        "approval.md": run_dir / DEFAULTS["approval_file"]
    }
    for template, target in template_targets.items():
        shutil.copyfile(TEMPLATES / template, target)

    state = {
        "run_id": run_id,
        "name": args.name,
        "references": args.reference,
        "target_screens": args.screen,
        "scope": args.scope,
        "current_stage": 1,
        "current_role": "research-agent",
        "human_approval": "pending",
        "stages": {"1": "in_progress", "2": "pending", "3": "pending", "4": "pending", "5": "pending"},
        "retry_counts": {"1": 0, "2": 0, "3": 0, "4": 0, "5": 0},
        "metrics": {"write_scope_violation_count": 0, "parallel_stage_count": 0, "gate_bypass_count": 0},
        "created_at": now_iso(),
        "updated_at": now_iso()
    }
    save_state(run_dir, state)
    set_active(run_id, "research-agent")
    print(json.dumps({"run_id": run_id, "run_dir": str(run_dir), "stage": 1, "role": "research-agent"}, ensure_ascii=False, indent=2))


def run_validation(run_dir):
    process = subprocess.run(
        [sys.executable, str(VALIDATOR), "--run", str(run_dir)],
        check=False,
        capture_output=True,
        text=True
    )
    try:
        payload = json.loads(process.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError("판정 스크립트 출력을 읽을 수 없습니다: {}".format(process.stderr.strip())) from exc
    return process.returncode, payload


def command_complete(args):
    run_dir = resolve_run(args.run)
    state = load_state(run_dir)
    stage = str(args.stage)
    if state["current_stage"] != args.stage or state["stages"].get(stage) != "in_progress":
        raise ValueError("현재 진행 중인 단계만 완료할 수 있습니다.")

    if stage != "5":
        source = run_dir / DEFAULTS["stage_sources"][stage]
        target = run_dir / DEFAULTS["stage_outputs"][stage]
        if not source.is_file():
            raise ValueError("단계 산출물이 없습니다: {}".format(source))
        shutil.copyfile(source, target)
    elif not (run_dir / DEFAULTS["stage_outputs"][stage]).is_file():
        raise ValueError("판정 결과가 없습니다. record-judge를 먼저 실행하세요.")

    return_code, result = run_validation(run_dir)
    if return_code != 0:
        state["retry_counts"][stage] += 1
        if state["retry_counts"][stage] > 2:
            state["stages"][stage] = "failed"
        save_state(run_dir, state)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return return_code

    if stage == "3":
        state["stages"][stage] = "waiting_approval"
        state["current_role"] = "orchestrator"
        set_active(args.run, "orchestrator")
    elif stage == "5":
        state["stages"][stage] = "passed"
        state["current_stage"] = None
        state["current_role"] = "orchestrator"
        state["completed_at"] = now_iso()
        set_active(args.run, "orchestrator")
    else:
        state["stages"][stage] = "passed"
        next_stage = args.stage + 1
        state["current_stage"] = next_stage
        state["stages"][str(next_stage)] = "in_progress"
        state["current_role"] = stage_role(next_stage)
        set_active(args.run, state["current_role"])

    save_state(run_dir, state)
    print(json.dumps({"run_id": args.run, "state": state}, ensure_ascii=False, indent=2))
    return 0


def write_approval(run_dir, status, approver="", return_stage="", note=""):
    content = "\n".join([
        "# 사람 승인 기록",
        "",
        "| 항목 | 값 |",
        "| --- | --- |",
        "| 상태 | {} |".format(status),
        "| 승인자 | {} |".format(approver),
        "| 승인 시각 | {} |".format(now_iso()),
        "| 반려 단계 | {} |".format(return_stage),
        "| 사유 또는 메모 | {} |".format(note.replace("|", "\\|")),
        ""
    ])
    (run_dir / DEFAULTS["approval_file"]).write_text(content, encoding="utf-8")


def command_approve(args):
    run_dir = resolve_run(args.run)
    state = load_state(run_dir)
    if state["stages"].get("3") != "waiting_approval":
        raise ValueError("키스크린 승인 대기 상태가 아닙니다.")
    state["human_approval"] = "approved"
    state["stages"]["3"] = "passed"
    state["stages"]["4"] = "in_progress"
    state["current_stage"] = 4
    state["current_role"] = "design-agent"
    write_approval(run_dir, "approved", args.approver, note=args.note)
    save_state(run_dir, state)
    set_active(args.run, "design-agent")
    print(json.dumps({"run_id": args.run, "stage": 4, "role": "design-agent"}, ensure_ascii=False, indent=2))


def command_reject(args):
    run_dir = resolve_run(args.run)
    state = load_state(run_dir)
    return_stage = str(args.return_stage)
    for stage_id in state["stages"]:
        numeric = int(stage_id)
        state["stages"][stage_id] = "passed" if numeric < args.return_stage else "pending"
    state["stages"][return_stage] = "in_progress"
    state["human_approval"] = "pending"
    state["current_stage"] = args.return_stage
    state["current_role"] = stage_role(args.return_stage)
    write_approval(run_dir, "rejected", return_stage=return_stage, note=args.reason)
    save_state(run_dir, state)
    set_active(args.run, state["current_role"])
    print(json.dumps({"run_id": args.run, "stage": args.return_stage, "role": state["current_role"]}, ensure_ascii=False, indent=2))


def command_resume(args):
    run_dir = resolve_run(args.run)
    state = load_state(run_dir)
    first = next((int(stage) for stage, status in state["stages"].items() if status != "passed"), None)
    if first is None:
        print(json.dumps({"run_id": args.run, "status": "complete"}, ensure_ascii=False))
        return
    status = state["stages"][str(first)]
    if status == "waiting_approval":
        role = "orchestrator"
    else:
        state["stages"][str(first)] = "in_progress"
        role = stage_role(first)
    state["current_stage"] = first
    state["current_role"] = role
    save_state(run_dir, state)
    set_active(args.run, role)
    print(json.dumps({"run_id": args.run, "stage": first, "role": role, "status": status}, ensure_ascii=False, indent=2))


def command_record_judge(args):
    run_dir = resolve_run(args.run)
    state = load_state(run_dir)
    if state["current_stage"] != 5 or state["stages"].get("5") != "in_progress":
        raise ValueError("가이드 검토 단계가 진행 중이 아닙니다.")
    payload = json.loads(args.result)
    required = {"checked_rules", "total_rules", "failed_rules", "unresolved_violations", "judge_write_attempts"}
    missing = sorted(required.difference(payload))
    if missing:
        raise ValueError("판정 결과 필드 누락: {}".format(", ".join(missing)))
    write_json(run_dir / DEFAULTS["stage_outputs"]["5"], payload)
    state["current_role"] = "orchestrator"
    save_state(run_dir, state)
    set_active(args.run, "orchestrator")
    print(json.dumps({"run_id": args.run, "recorded": True}, ensure_ascii=False))


def command_status(args):
    run_dir = resolve_run(args.run)
    print(json.dumps(load_state(run_dir), ensure_ascii=False, indent=2))


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    start = subparsers.add_parser("start")
    start.add_argument("--name", required=True)
    start.add_argument("--reference", action="append", required=True)
    start.add_argument("--screen", action="append", required=True)
    start.add_argument("--scope", default="이번 실행에서 지정한 화면 범위")
    start.set_defaults(handler=command_start)

    complete = subparsers.add_parser("complete-stage")
    complete.add_argument("--run", required=True)
    complete.add_argument("--stage", type=int, choices=range(1, 6), required=True)
    complete.set_defaults(handler=command_complete)

    approve = subparsers.add_parser("approve")
    approve.add_argument("--run", required=True)
    approve.add_argument("--approver", required=True)
    approve.add_argument("--note", default="")
    approve.set_defaults(handler=command_approve)

    reject = subparsers.add_parser("reject")
    reject.add_argument("--run", required=True)
    reject.add_argument("--return-stage", type=int, choices=range(1, 4), required=True)
    reject.add_argument("--reason", required=True)
    reject.set_defaults(handler=command_reject)

    resume = subparsers.add_parser("resume")
    resume.add_argument("--run", required=True)
    resume.set_defaults(handler=command_resume)

    record = subparsers.add_parser("record-judge")
    record.add_argument("--run", required=True)
    record.add_argument("--result", required=True)
    record.set_defaults(handler=command_record_judge)

    status = subparsers.add_parser("status")
    status.add_argument("--run", required=True)
    status.set_defaults(handler=command_status)
    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    try:
        result = args.handler(args)
        return int(result or 0)
    except (ValueError, RuntimeError, OSError, json.JSONDecodeError) as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
