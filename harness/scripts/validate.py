#!/usr/bin/env python3
"""Validate one design-workflow harness run with standard-library Python."""

import argparse
import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RULES = ROOT / "harness" / "rules.yaml"


class FormatError(Exception):
    pass


def load_json(path):
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except FileNotFoundError as exc:
        raise FormatError("필수 파일이 없습니다: {}".format(path)) from exc
    except json.JSONDecodeError as exc:
        raise FormatError("JSON 형식 오류: {}:{}".format(path, exc.lineno)) from exc


def parse_scalar(raw):
    value = raw.strip()
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value.strip('"\'')


def load_frontmatter(path):
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError as exc:
        raise FormatError("필수 파일이 없습니다: {}".format(path)) from exc

    if not lines or lines[0].strip() != "---":
        raise FormatError("YAML front matter 시작 구분자가 없습니다: {}".format(path))

    data = {}
    for line in lines[1:]:
        if line.strip() == "---":
            return data
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if ":" not in line:
            raise FormatError("front matter 형식 오류: {}: {}".format(path, line))
        key, raw = line.split(":", 1)
        data[key.strip()] = parse_scalar(raw)

    raise FormatError("YAML front matter 종료 구분자가 없습니다: {}".format(path))


def nested_value(data, dotted_path):
    current = data
    for part in dotted_path.split("."):
        if not isinstance(current, dict) or part not in current:
            raise FormatError("규칙 경로가 없습니다: {}".format(dotted_path))
        current = current[part]
    return current


def evaluate(check, metadata, design_rules):
    field = check["field"]
    actual = metadata.get(field)
    operator = check["operator"]

    if operator == "eq":
        expected = check["value"]
        passed = actual == expected
    elif operator == "gte":
        expected = check["value"]
        passed = isinstance(actual, (int, float)) and actual >= expected
    elif operator == "between":
        expected = [check["min"], check["max"]]
        passed = isinstance(actual, (int, float)) and check["min"] <= actual <= check["max"]
    elif operator in ("eq_rule", "gte_rule", "subset_rule"):
        expected = nested_value(design_rules, check["rule"])
        if operator == "eq_rule":
            passed = actual == expected
        elif operator == "gte_rule":
            passed = isinstance(actual, (int, float)) and actual >= expected
        else:
            passed = isinstance(actual, list) and set(actual).issubset(set(expected))
    elif operator == "eq_field":
        expected = metadata.get(check["other_field"])
        passed = actual == expected
    else:
        raise FormatError("지원하지 않는 연산자입니다: {}".format(operator))

    return passed, actual, expected


def validate_state(state, rules):
    format_errors = []
    gate_errors = []
    stages = state.get("stages")
    if not isinstance(stages, dict):
        return ["state.json의 stages가 객체가 아닙니다."], [], 1

    allowed = set(rules["status_values"])
    statuses = []
    for stage_id in rules["stages"]:
        status = stages.get(stage_id)
        if status not in allowed:
            format_errors.append("{}단계 상태가 유효하지 않습니다: {}".format(stage_id, status))
        statuses.append(status)

    active_count = sum(status in ("in_progress", "waiting_approval") for status in statuses)
    if active_count > 1:
        gate_errors.append("parallel_stage_count가 0이 아닙니다.")

    first_non_passed = next((index + 1 for index, status in enumerate(statuses) if status != "passed"), len(statuses) + 1)
    for index, status in enumerate(statuses, start=1):
        if index > first_non_passed and status not in ("pending", None):
            gate_errors.append("gate_bypass_count가 0이 아닙니다: {}단계".format(index))

    metrics = state.get("metrics", {})
    for field in ("write_scope_violation_count", "parallel_stage_count", "gate_bypass_count"):
        if metrics.get(field, 0) != 0:
            gate_errors.append("{}가 0이 아닙니다.".format(field))

    retry_counts = state.get("retry_counts", {})
    for stage_id, retry_count in retry_counts.items():
        if retry_count > rules["max_retries_per_stage"]:
            gate_errors.append("{}단계 재시도 횟수가 한도를 초과했습니다.".format(stage_id))

    approval = state.get("human_approval", "pending")
    stage_three_status = stages.get("3")
    later_started = any(stages.get(stage_id) != "pending" for stage_id in ("4", "5"))
    if approval != "approved" and (stage_three_status == "waiting_approval" or later_started):
        gate_errors.append("사람 승인 없이 4단계 이후로 진행할 수 없습니다.")

    if "failed" in statuses:
        gate_errors.append("실패 상태인 단계가 있습니다.")

    return format_errors, gate_errors, first_non_passed


def validate_run(run_dir, rules_path=DEFAULT_RULES):
    format_errors = []
    gate_errors = []
    checked = []

    try:
        rules = load_json(rules_path)
        design_rules = load_json(ROOT / rules["design_rules_file"])
        state = load_json(run_dir / "state.json")
    except FormatError as exc:
        return {"passed": False, "exit_code": 2, "return_stage": 1, "format_errors": [str(exc)], "gate_errors": [], "checked_artifacts": []}

    required_context = rules.get("source_documents", []) + rules.get("required_context_files", [])
    missing_context = [path for path in required_context if not (ROOT / path).is_file()]
    if missing_context:
        format_errors.append("필수 컨텍스트 파일 누락: {}".format(", ".join(missing_context)))

    run_id = state.get("run_id")
    if run_id != run_dir.name:
        format_errors.append("state.json의 run_id가 실행 폴더명과 일치하지 않습니다.")
    elif not re.fullmatch(rules["run_id_pattern"], run_id):
        format_errors.append("run_id 형식이 YYYYMMDD-HHMM-작업명과 일치하지 않습니다.")

    if len(rules.get("categories", [])) != 7:
        format_errors.append("초기 카테고리 수가 7개가 아닙니다.")

    state_format, state_gates, resume_stage = validate_state(state, rules)
    format_errors.extend(state_format)
    gate_errors.extend(state_gates)

    stages_state = state.get("stages", {})
    for stage_id, stage_rule in rules["stages"].items():
        if stages_state.get(stage_id) == "pending":
            continue

        artifact_path = run_dir / stage_rule["artifact"]
        try:
            if stage_rule["format"] == "markdown_frontmatter":
                metadata = load_frontmatter(artifact_path)
            else:
                metadata = load_json(artifact_path)
        except FormatError as exc:
            format_errors.append(str(exc))
            continue

        checked.append(stage_rule["artifact"])
        missing = [key for key in stage_rule["required_metadata"] if key not in metadata]
        if missing:
            format_errors.append("{} 필수 판정값 누락: {}".format(stage_rule["artifact"], ", ".join(missing)))
            continue

        stage_checks = list(stage_rule["gates"])
        if stage_id != "5":
            stage_checks.extend(rules["service_invariants"])

        for check in stage_checks:
            try:
                passed, actual, expected = evaluate(check, metadata, design_rules)
            except FormatError as exc:
                format_errors.append(str(exc))
                continue
            if not passed:
                gate_errors.append(
                    "{}: {} 판정 실패 (actual={!r}, expected={!r})".format(
                        stage_rule["artifact"], check["field"], actual, expected
                    )
                )
                resume_stage = min(resume_stage, stage_rule["return_stage"])

    if format_errors:
        exit_code = 2
    elif gate_errors:
        exit_code = 1
    else:
        exit_code = 0

    return {
        "passed": exit_code == 0,
        "exit_code": exit_code,
        "return_stage": resume_stage if exit_code else None,
        "format_errors": format_errors,
        "gate_errors": gate_errors,
        "checked_artifacts": checked,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", required=True, help="runs/<run-id> 경로")
    parser.add_argument("--rules", default=str(DEFAULT_RULES), help="하네스 규칙 파일")
    args = parser.parse_args()

    run_dir = Path(args.run).resolve()
    rules_path = Path(args.rules).resolve()
    result = validate_run(run_dir, rules_path)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return result["exit_code"]


if __name__ == "__main__":
    sys.exit(main())
