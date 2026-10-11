# R5 게이트

## 자동 게이트

| 게이트 | 통과 조건 | 실패 시 복귀 |
| --- | --- | --- |
| 분석 완료 | `references >= 1`, `missing_source_count == 0`, `reflection_candidates >= 1` | 1단계 |
| 화면 설계 완료 | `2 <= planned_key_screens <= 3`, `missing_required_sections == 0` | 2단계 |
| 키스크린 완료 | `2 <= key_screens <= 3`, 모든 프레임이 `390x844` | 3단계 |
| 서비스 원칙 준수 | `unknown_category_count == 0`, `unverified_fact_count == 0` | 위반이 생긴 단계 |
| 최종 가이드 준수 | `rules/design-rules.json` 판정 완료, `checked_rules == total_rules`, `failed_rules == 0` | 4단계 |

`unknown_category_count == 0`과 `unverified_fact_count == 0`은 `docs/story-service.md`에 정의된 다음 원칙을 검사한다.

- 자동 분류는 기존 카테고리 7개만 사용하며 새로운 카테고리를 임의로 만들지 않는다.
- 확인되지 않은 설명이나 URL을 사실처럼 채우지 않는다.

디자인 토큰과 수치 기준은 `rules/design-rules.json`에서 읽으며 다른 판정 파일에 값을 복제하지 않는다.

## 사람 승인

사람 승인 지점은 3단계 키스크린 제작 후 한 곳으로 제한한다.

내부 관계자는 아래 항목을 함께 확인한다.

- 레퍼런스 분석 방향
- 화면 설계
- UI 키스크린 2~3개

`human_approval == approved`일 때만 4단계 디자인 제작을 시작한다.

승인이 반려되면 반려 기록의 `return_stage` 값에 지정된 단계로 복귀한다.

## 구조화된 판정값

`01-reference-analysis.md`, `02-screen-spec.md`, `03-key-screens.md`, `04-design-output.md` 상단에 YAML front matter를 둔다. 각 파일은 해당 단계의 필수 판정값을 front matter에 기록한다.

아래 조건을 만족할 때만 게이트 판정을 실행한다.

`metadata_missing_count == 0`

필수 판정값이 누락되면 해당 단계의 상태를 `failed`로 기록하고 같은 단계로 복귀한다.

## 최종 통과

아래 조건을 모두 만족해야 파이프라인을 완료 처리한다.

- 모든 자동 게이트가 통과했다.
- `human_approval == approved`이다.
- `failed_rules == 0`이다.
- `unresolved_violations == 0`이다.
