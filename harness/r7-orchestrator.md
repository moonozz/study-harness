# R7 오케스트레이터

## 진입점

프로젝트 루트의 `AGENTS.md`를 하네스 오케스트레이터의 단일 진입점으로 사용한다.

Codex는 `.codex/skills/run-design-harness/SKILL.md`를 실행 워크플로로 사용하고 `.codex/hooks.json`으로 쓰기 범위와 중단 조건을 강제한다.

`AGENTS.md`는 전체 라운드가 끝난 뒤 초안을 검토하고 사용자의 승인을 받은 후 생성한다.

## 실행 전 필수 문서

오케스트레이터는 실행 전에 아래 파일을 확인한다.

- `docs/prd.md`
- `docs/design.md`
- `docs/story-service.md`
- `docs/story-work.md`
- `harness/r2-purpose.md`
- `harness/r3-pipeline.md`
- `harness/r4-artifacts.md`
- `harness/r5-gates.md`
- `harness/r6-roles.md`
- `harness/rules.yaml`
- `rules/design-rules.json`
- `harness/defaults.yaml`
- `.codex/skills/run-design-harness/SKILL.md`
- `.codex/hooks.json`

실행 조건은 아래와 같다.

`missing_required_files == 0`

## 순차 실행

오케스트레이터는 한 번에 현재 단계 하나만 실행한다.

각 단계는 아래 순서를 따른다.

1. 현재 단계 입력과 상태를 확인한다.
2. 담당 에이전트를 실행한다.
3. 단계 산출물을 생성한다.
4. 자동 게이트를 실행한다.
5. 결과를 `state.json`에 저장한다.

순차 실행의 통과 조건은 아래와 같다.

- `parallel_stage_count == 0`
- `gate_bypass_count == 0`

## 단계 시작 전 재확인

각 단계 시작 전에 아래 항목을 다시 확인한다.

- 현재 단계의 필수 입력 파일이 존재한다.
- 이전 단계의 게이트가 통과 상태다.
- 담당 에이전트의 편집 경로가 허용 범위 안이다.
- `harness/rules.yaml`과 이 파일이 참조하는 `rules/design-rules.json`을 읽을 수 있다.

하나라도 통과하지 못하면 해당 단계를 시작하지 않는다.

## 실패와 승인 대기

자동 게이트가 실패하면 같은 단계를 최대 2회 재시도한다. 두 번째 재시도 후에도 실패하면 `state == failed`로 기록하고 실행을 중단한다.

사람 승인이 필요한 지점에 도달하면 `state == waiting_approval`로 기록하고 실행을 중단한다. `human_approval == approved`가 기록되기 전에는 4단계를 시작하지 않는다.
