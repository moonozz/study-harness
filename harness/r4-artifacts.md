# R4 산출물

## 실행 폴더

각 실행의 산출물은 아래 경로에 분리해 저장한다.

`runs/<run-id>/`

`run-id`는 `YYYYMMDD-HHMM-작업명` 형식을 사용한다.

## 단계별 대표 파일

| 단계 | 대표 파일 | 기록 내용 |
| --- | --- | --- |
| 1. 레퍼런스 분석 | `01-reference-analysis.md` | 레퍼런스 수집본, 분석 결과, 서비스 반영 후보 |
| 2. 화면 설계 | `02-screen-spec.md` | 화면 구조와 화면별 설계 내용 |
| 3. 키스크린 제작 | `03-key-screens.md` | Figma 프레임 링크, 프레임 수, 프레임 크기 |
| 4. 디자인 제작 | `04-design-output.md` | Figma 프레임 링크, 디자인 토큰, 컴포넌트, 화면 디자인 |
| 5. 가이드 검토 | `05-guide-check.json` | 규칙별 통과 여부와 위반 항목 |

## 규칙의 단일 기준

규칙 종류별 SSOT를 아래와 같이 분리한다.

| 규칙 종류 | SSOT |
| --- | --- |
| 파이프라인·게이트·상태 규칙 | `harness/rules.yaml` |
| 디자인 토큰·수치 규칙 | `rules/design-rules.json` |

`harness/rules.yaml`은 디자인 수치를 복제하지 않고 `rules/design-rules.json`의 경로를 참조한다.

## 실행 상태와 재개

각 실행 폴더에 `state.json`을 저장한다.

단계 상태는 아래 값 중 하나만 사용한다.

- `pending`
- `in_progress`
- `waiting_approval`
- `passed`
- `failed`

재개 시 단계 순서대로 상태를 확인하고, 처음 발견된 `passed`가 아닌 단계부터 시작한다.
