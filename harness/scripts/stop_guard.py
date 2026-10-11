#!/usr/bin/env python3
"""Continue an active turn when a harness stage is still in progress."""

import json

from hook_common import RUNS_ROOT, read_active, read_input


def main():
    event = read_input()
    active = read_active()
    if not active or event.get("stop_hook_active"):
        print("{}")
        return 0

    state_path = RUNS_ROOT / active["run_id"] / "state.json"
    if not state_path.is_file():
        print("{}")
        return 0
    state = json.loads(state_path.read_text(encoding="utf-8"))
    stage = state.get("current_stage")
    status = state.get("stages", {}).get(str(stage)) if stage else None
    if status == "in_progress":
        print(json.dumps({
            "decision": "block",
            "reason": "하네스 {}단계가 진행 중입니다. 산출물을 완성하고 complete-stage를 실행하거나 실패 상태를 기록하세요.".format(stage)
        }, ensure_ascii=False))
    else:
        print("{}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
