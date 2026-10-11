"""Shared helpers for project-local Codex hooks."""

import json
import os
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
RUNS_ROOT = Path(os.environ.get("HARNESS_RUNS_ROOT", ROOT / "runs")).resolve()
ACTIVE_PATH = RUNS_ROOT / ".active.json"


def read_input():
    raw = sys.stdin.read()
    return json.loads(raw) if raw.strip() else {}


def read_active():
    if not ACTIVE_PATH.is_file():
        return None
    try:
        return json.loads(ACTIVE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def deny(reason):
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason
        }
    }, ensure_ascii=False))


def patch_paths(command):
    return re.findall(r"^\*\*\* (?:Add|Update|Delete) File: (.+)$", command, flags=re.MULTILINE)


def is_mutating_shell(command):
    patterns = [
        r"(^|\s)(rm|mv|cp|touch|mkdir|install)(\s|$)",
        r"(^|\s)(sed\s+-i|perl\s+-pi)(\s|$)",
        r"(^|[^<])>{1,2}([^>]|$)",
        r"(^|\s)tee(\s|$)",
        r"git\s+(add|commit|checkout|reset|clean|restore|switch|merge|rebase)",
    ]
    return any(re.search(pattern, command) for pattern in patterns)


def is_orchestrator_command(command):
    return "harness/scripts/orchestrate.py" in command
