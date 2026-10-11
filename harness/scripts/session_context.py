#!/usr/bin/env python3
"""Add concise harness context when a Codex session starts or resumes."""

import json

from hook_common import read_active, read_input


def main():
    event = read_input()
    active = read_active()
    message = "이 저장소의 디자인 작업은 $run-design-harness 스킬과 AGENTS.md를 따른다."
    if active:
        message += " 활성 실행은 {run_id}, 현재 역할은 {role}이다.".format(**active)
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": message
        }
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
