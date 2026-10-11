# Figma Design Guide

Figma 작업의 의미 기준은 `docs/design.md`, 기계 판정값은 `rules/design-rules.json`을 사용한다. 이 문서에는 토큰 값을 복제하지 않는다.

## 키스크린 기록

`03-key-screens.md`의 front matter에 아래 값을 기록한다.

- `key_screens`: 키스크린 개수
- `frame_width`, `frame_height`: 모든 키스크린의 공통 프레임 크기
- `figma_frame_urls`: 키스크린 프레임 URL 목록

프레임 크기가 서로 다르면 공통값을 기록하지 말고 `frame_size_mismatch_count`를 본문에 명시한 뒤 게이트를 실패 처리한다.

## 디자인 결과 기록

`04-design-output.md`의 front matter에는 실제 사용된 값만 기록한다.

- `used_color_values`
- `used_radii_px`
- `shadow_count`
- `decorative_gradient_count`
- `minimum_touch_target_px`
- `mobile_input_font_size_px`
- `letter_spacing`

Figma 링크만으로 값을 확인할 수 없으면 추정하지 않는다. 확인하지 못한 값은 본문에 남기고 사용자에게 확인을 요청한다.
