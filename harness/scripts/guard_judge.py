#!/usr/bin/env python3
"""Keep the judge role read-only while allowing the orchestrator handoff command."""

from hook_common import deny, is_mutating_shell, is_orchestrator_command, read_active, read_input


def main():
    event = read_input()
    active = read_active()
    if not active or active.get("role") != "judge-agent":
        return 0

    tool_name = event.get("tool_name", "")
    command = event.get("tool_input", {}).get("command", "")
    if is_orchestrator_command(command) and " record-judge " in " {} ".format(command):
        return 0
    if tool_name == "apply_patch" or (tool_name == "Bash" and is_mutating_shell(command)):
        deny("judge-agent는 읽기 전용입니다. 판정 JSON은 표준 출력으로 반환하세요.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
