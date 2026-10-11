#!/usr/bin/env python3
"""Block active harness agents from writing outside their assigned run folder."""

import json
from pathlib import Path

from hook_common import RUNS_ROOT, deny, is_mutating_shell, is_orchestrator_command, patch_paths, read_active, read_input


def allowed_roots(active):
    run_root = (RUNS_ROOT / active["run_id"]).resolve()
    role = active.get("role")
    mapping = {
        "research-agent": [run_root / "agents" / "research"],
        "screen-agent": [run_root / "agents" / "screen"],
        "design-agent": [run_root / "agents" / "design"],
        "judge-agent": [],
        "orchestrator": [run_root]
    }
    return [path.resolve() for path in mapping.get(role, [])]


def within(path, roots, cwd):
    resolved = path if path.is_absolute() else Path(cwd) / path
    resolved = resolved.resolve()
    return any(resolved == root or root in resolved.parents for root in roots)


def main():
    event = read_input()
    active = read_active()
    if not active:
        return 0

    role = active.get("role")
    tool_name = event.get("tool_name", "")
    command = event.get("tool_input", {}).get("command", "")
    cwd = event.get("cwd") or str(Path.cwd())
    roots = allowed_roots(active)

    if is_orchestrator_command(command):
        return 0

    if tool_name == "apply_patch":
        paths = patch_paths(command)
        if not paths:
            deny("활성 하네스 실행 중에는 대상 경로를 확인할 수 없는 패치를 허용하지 않습니다.")
            return 0
        invalid = [path for path in paths if not within(Path(path), roots, cwd)]
        if invalid:
            deny("{}의 편집 범위를 벗어났습니다: {}".format(role, ", ".join(invalid)))
    elif tool_name == "Bash" and is_mutating_shell(command):
        deny("활성 하네스 실행 중의 셸 쓰기는 차단됩니다. 허용 폴더에는 apply_patch를 사용하세요.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
