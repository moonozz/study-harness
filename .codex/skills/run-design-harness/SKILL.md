---
name: run-design-harness
description: Start, resume, approve, reject, or validate this repository's staged reference-analysis and UI-design harness. Use for the natural-language harness triggers defined in AGENTS.md; do not use for ordinary design questions that are not starting or changing a harness run.
---

# Run Design Harness

Use `AGENTS.md` as the durable project instruction and `harness/rules.yaml` as the pipeline rule source.

## Route the request

- New run: read the required inputs and execute `harness/scripts/orchestrate.py start`.
- Resume: execute `orchestrate.py resume`, then inspect the returned stage and role.
- Key-screen approval: execute `orchestrate.py approve` only after explicit human approval.
- Rejection: execute `orchestrate.py reject` with the user's return stage and reason.
- Status: execute `orchestrate.py status` without changing stage data.

If a required trigger value is missing, ask only for that value. Do not infer references, target screens, approval, rejection reasons, or unverified product facts.

## Execute one stage

1. Read [references/roles.md](references/roles.md) for the current role only.
2. Work only in the role's assigned folder under `runs/<run-id>/agents/`.
3. Fill the existing stage template, including every front-matter field.
4. Run `python3 harness/scripts/orchestrate.py complete-stage --run <run-id> --stage <n>`.
5. Stop when the state becomes `waiting_approval` or `failed`.

Stages are sequential. Do not start, delegate, or edit a later stage before the previous gate passes. A subagent may handle the current role, but subagents must run one at a time because these stages share mutable state.

## Judge boundary

The judge reads the run outputs, `docs/design.md`, and `rules/design-rules.json`. It must not edit files. Return the judgement as JSON with these fields:

```json
{
  "checked_rules": 0,
  "total_rules": 0,
  "failed_rules": 0,
  "unresolved_violations": 0,
  "judge_write_attempts": 0
}
```

After the judge returns, the orchestrator records that JSON with `record-judge` and completes stage 5.

## Verify

Run both commands before reporting harness completion:

```bash
python3 harness/scripts/validate.py --run runs/<run-id>
python3 -m unittest discover -s harness/tests -p 'test_*.py' -v
```
