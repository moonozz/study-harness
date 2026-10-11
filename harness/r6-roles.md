# R6 역할과 권한

## 역할 분리

Codex 실행 시 역할별 상세 지침은 `.codex/skills/run-design-harness/references/roles.md`에서 읽는다. 역할은 독립된 상시 프로세스가 아니라 오케스트레이터가 현재 단계에 맞춰 순차적으로 부여하는 경계다.

| 역할 | 담당 |
| --- | --- |
| `research-agent` | 1단계 레퍼런스 분석 |
| `screen-agent` | 2단계 화면 설계 |
| `design-agent` | 3~4단계 키스크린 제작과 디자인 제작 |
| `judge-agent` | 5단계 규칙 판정 |
| `orchestrator` | 단계 실행, 상태 기록, 승인 대기, 복귀 처리 |

## 편집 범위

| 에이전트 | 편집 가능 폴더 |
| --- | --- |
| `research-agent` | `runs/<run-id>/agents/research/` |
| `screen-agent` | `runs/<run-id>/agents/screen/` |
| `design-agent` | `runs/<run-id>/agents/design/` |
| `orchestrator` | `runs/<run-id>/` |

각 작업 에이전트는 지정된 폴더 하나에서만 파일을 생성하거나 수정할 수 있다.

`write_scope_violation_count > 0`이면 해당 단계를 즉시 실패 처리한다.

## 읽기 전용 판정자

`judge-agent`는 프로젝트 전체 파일을 읽을 수 있지만 생성, 수정, 삭제할 수 없다.

판정 결과는 JSON 형식의 표준 출력으로 반환한다. `orchestrator`만 판정 결과를 `runs/<run-id>/05-guide-check.json`에 기록한다.

판정자 권한의 통과 조건은 아래와 같다.

`judge_write_attempts == 0`

## 자연어 트리거

### 새 작업 시작

```text
새 작업 시작: 작업명=<이름>, 레퍼런스=<입력>, 대상 화면=<이름>
```

### 작업 재개

```text
작업 재개: run_id=<실행 ID>
```

### 사람 승인

```text
키스크린 승인: run_id=<실행 ID>
```

### 승인 반려

```text
반려: run_id=<실행 ID>, return_stage=<1~3>, reason=<사유>
```

트리거별 필수 키가 하나라도 없으면 실행하지 않는다. `orchestrator`는 누락된 키만 사용자에게 다시 묻는다.
