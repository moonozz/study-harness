# Design Workflow Harness

## Codex 실행

이 저장소의 실행 스킬은 `.codex/skills/run-design-harness/SKILL.md`다. 아래 자연어 트리거가 들어오거나 사용자가 `$run-design-harness`를 지정하면 해당 스킬을 사용한다.

프로젝트 설정과 강제 훅은 `.codex/config.toml`, `.codex/hooks.json`에 있다. 하네스 실행 중에는 훅이 역할별 편집 범위와 `judge-agent`의 읽기 전용 정책을 검사한다.

## 목적

이 저장소의 작업을 레퍼런스 분석, 화면 설계, 키스크린 제작, 디자인 제작, 가이드 검토 순서로 실행한다.

서비스 기준과 실제 작업 방식은 서로 다른 문서로 관리한다. 두 내용을 합치거나 한 문서의 내용을 다른 문서의 근거로 추정하지 않는다.

## 기준 문서

실행 전에 아래 파일을 모두 읽는다.

- `docs/prd.md`
- `docs/design.md`
- `docs/story-service.md`
- `docs/story-work.md`
- `harness/r2-purpose.md`
- `harness/r3-pipeline.md`
- `harness/r4-artifacts.md`
- `harness/r5-gates.md`
- `harness/r6-roles.md`
- `harness/r7-orchestrator.md`
- `harness/r8-validation.md`
- `harness/defaults.yaml`
- `harness/rules.yaml`
- `rules/design-rules.json`
- `.codex/skills/run-design-harness/SKILL.md`

파이프라인·게이트·상태 판정값은 `harness/rules.yaml`, 디자인 토큰·수치 판정값은 `rules/design-rules.json`만 SSOT로 사용한다. PRD나 기준 문서에 없는 내용은 추정하지 말고 사용자에게 묻는다. `missing_required_files > 0`이면 작업을 시작하지 않는다.

## 실행 트리거

다음 자연어 형식을 인식한다.

- `새 작업 시작: 작업명=<이름>, 레퍼런스=<입력>, 대상 화면=<이름>`
- `작업 재개: run_id=<실행 ID>`
- `키스크린 승인: run_id=<실행 ID>`
- `반려: run_id=<실행 ID>, return_stage=<1~3>, reason=<사유>`

필수 값이 누락되면 실행하지 않고 누락된 값만 사용자에게 묻는다.

## 실행 구조

실행 폴더는 `runs/<YYYYMMDD-HHMM-작업명>/` 형식을 사용한다. 각 실행의 현재 상태는 `state.json`에 기록한다.

단계 상태는 다음 값만 허용한다.

- `pending`
- `in_progress`
- `waiting_approval`
- `passed`
- `failed`

## 파이프라인

| 단계 | 담당 | 대표 산출물 |
| --- | --- | --- |
| 1. 레퍼런스 분석 | `research-agent` | `01-reference-analysis.md` |
| 2. 화면 설계 | `screen-agent` | `02-screen-spec.md` |
| 3. 키스크린 제작 | `design-agent` | `03-key-screens.md` |
| 4. 디자인 제작 | `design-agent` | `04-design-output.md` |
| 5. 가이드 검토 | `judge-agent` | `05-guide-check.json` |

한 번에 한 단계만 실행한다. 이전 산출물과 게이트 통과 기록이 없으면 다음 단계로 넘어가지 않는다.

각 단계는 입력 확인, 에이전트 실행, 산출물 생성, 자동 게이트 실행, 상태 저장 순서로 처리한다.

## 역할과 권한

- `research-agent`는 `runs/<run-id>/agents/research/`만 편집한다.
- `screen-agent`는 `runs/<run-id>/agents/screen/`만 편집한다.
- `design-agent`는 `runs/<run-id>/agents/design/`만 편집한다.
- `orchestrator`는 해당 `runs/<run-id>/`만 편집한다.
- `judge-agent`는 읽기 전용이며 파일을 생성·수정·삭제하지 않는다.

`judge-agent`는 판정 JSON을 표준 출력으로 반환한다. `orchestrator`만 이를 `05-guide-check.json`에 기록한다.

허용 범위 밖의 파일 변경이 발생하면 즉시 실패 처리한다.

## 게이트와 승인

모든 자동 게이트는 `harness/rules.yaml`로 판정한다.

서비스 원칙 검사에는 다음 항목이 반드시 포함되어야 한다.

- 기존 7개 목록에 없는 카테고리를 임의로 생성하지 않는다.
- 확인되지 않은 설명이나 URL을 사실처럼 기록하지 않는다.

사람 승인 지점은 3단계 키스크린 제작 후 한 곳이다. `human_approval == approved` 전에는 4단계를 시작하지 않는다.

반려되면 `return_stage`로 복귀한다. 최종 가이드 위반이 발견되면 4단계로 복귀한다.

## 실패와 재개

자동 게이트 실패 시 같은 단계를 최대 2회 재시도한다. 재시도 후에도 실패하면 상태를 `failed`로 기록하고 중단한다.

사람 승인이 필요하면 `waiting_approval`로 기록하고 중단한다. 재개 시 처음 발견된 `passed`가 아닌 단계부터 시작한다.

게이트를 우회하거나 여러 단계를 병렬로 실행하지 않는다.

## 검증

아래 명령으로 실행 결과를 검증한다.

`python3 harness/scripts/validate.py --run runs/<run-id>`

전체 하네스 테스트는 아래 명령으로 실행한다.

`python3 -m unittest discover -s harness/tests -p 'test_*.py' -v`

종료 코드 의미는 다음과 같다.

- `0`: 검증 통과
- `1`: 게이트 실패
- `2`: 규칙 또는 입력 형식 오류

검증 결과는 `harness/verification-report.md`에 기록한다. 모든 필수 검증 시나리오가 통과하기 전에는 하네스를 완료 처리하지 않는다.
