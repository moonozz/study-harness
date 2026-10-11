# Harness Roles

Read only the section for the current role.

## research-agent

- Read: `docs/prd.md`, `docs/story-service.md`, supplied references.
- Edit: `runs/<run-id>/agents/research/` only.
- Produce: `01-reference-analysis.md`.
- Do not invent missing reference facts or service URLs.

## screen-agent

- Read: approved reference analysis, `docs/prd.md`, `docs/story-service.md`.
- Edit: `runs/<run-id>/agents/screen/` only.
- Produce: `02-screen-spec.md` with 2~3 planned key screens.
- Preserve service context separately from the manual work record.

## design-agent

- Read: approved screen specification, `docs/design.md`, `rules/design-rules.json`, `harness/guides/figma-design-guide.md`.
- Edit: `runs/<run-id>/agents/design/` only.
- Produce: `03-key-screens.md`, then `04-design-output.md` after human approval.
- Key screens must be 2~3 frames at `390x844`.

## judge-agent

- Read: all run outputs and rule sources.
- Edit: nothing.
- Return: judgement JSON in the final response or standard output.
- Any write attempt makes the gate fail.

## orchestrator

- Edit: the active `runs/<run-id>/` directory only.
- Own: state transitions, promotion of validated artifacts, approval records, and judge-result recording.
- Never bypass a gate or create human approval on the user's behalf.
