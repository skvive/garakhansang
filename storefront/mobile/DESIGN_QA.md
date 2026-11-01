# 가락한상 모바일 전용 디자인/QA — 2026-11-01

## 범위 및 설계 의도
원본 PC UI 보호 + 모바일 전용 URL 및 UI 레이어 분리.
- 홈: `/mobile/index.html`
- 매장 찾기: `/mobile/index.html?view=stores`
- 참고 시세: `/mobile/index.html?view=prices`
- 레시피: `/mobile/index.html?view=recipes`
- 용기수산: `/mobile/merchant.html?store=yonggi-susan`
- 일월수산: `/mobile/merchant.html?store=ilwol-susan`
- 레시피 상세: `/mobile/recipe.html?id=recipe-002` (전체 132개 데이터 공유)

## 사용자 첨부 스크린샷 진단
1. 모바일에서 PC 데스크톱 뷰가 축소되어 텍스트·버튼·메뉴가 작게 보임.
2. 용기수산 PC식 2열 히어로 및 정보 박스의 압축/축소 문제.
3. 레시피 페이지에서는 `align-items:center`로 사진과 제목의 시작점이 달라 큰 빈 여백 발생.
4. 일부 광어 요리의 합성 사진이 실제 식재료와 일치하는지 검증되지 않음.

## 모바일 디자인 시스템
- 독립 `mobile.css` / `mobile.js`: 원본 데스크톱 CSS·JS와 충돌하지 않음.
- 390px 기본 본문 16px; 클릭/버튼 최소 44px.
- 하단 탭: 홈/매장/시세/레시피/지도; 상단 햄버거·검색 링크.
- 매장 사진·메뉴 목록 1열, 실제 캡처 기반 참조가격과 확인 필요 안내.
- 레시피 상세: 제목 → 식재료 참고사진 → 재료 체크 → 조리 단계.
- 스마트폰의 '데스크톱 사이트 요청'으로 터치 환경이 980px CSS viewport가 될 때 가독성을 위해 폰트/버튼/여백을 확대 적용.
- Android/터치 기기 자동 모바일 안내; `?desktop=1`로 PC 버전 선택 가능.
- 모바일 대상은 원본 HTML의 SEO 링크 구조를 유지하고, 원본 PC URL도 유효함.
- 실시간 경매 정보·실매출·쿠폰·제휴·주문 기능은 주장하지 않음.

## 브라우저 QA (원격 Chromium)
- 모바일 7개 화면 × 폭 320,360,390,430,768,980px = **42/42 PASS**.
- 390px, 980px에서 용기수산 메뉴 24개; 새우 검색/오마카세 필터 정상.
- 레시피 002 재료 4개, 체크박스 정상, 광어 참고 이미지 정상.
- 안드로이드 일반/데스크톱모드 및 PC 데스크톱 원본 URL 모바일 라우팅 15/15 PASS.
- PC 레시피 데스크톱 폭 1182px에서 좌우 시작점 차이 7px, 참고 사진 약 390px 높이, 페이지 가로 넘침 0.
- 실제 Samsung Internet/Chrome Android 16 물리 기기의 별도 육안 테스트와 OS 설정 조합 검증은 미실시.
- Google Maps 외부 지도 API 실제 수급 및 상인 가격·영업 현황은 이번 디자인 QA 범위 밖.

## 디자인 미리보기
- 3화면: 모바일 홈 / 용기수산 / 광어 간장무조림
- https://d2ol7oe51mr4n9.cloudfront.net/user_3HQYBhFdk9zQhjBPuuu0mHjev2G/242ff42e-0880-406a-aefe-9aa4b5dd1308.jpg

## 참고/주의
제공된 모바일 레시피 식재료 이미지는 실제 조리 완성 사진이 아닙니다. 기존 PC `recipe-002.html`의 잘못 표현될 수 있는 이미지도 광어 식재료 사진으로 변경했습니다.
미검증 점포 호수, 현행 가격, 실시간 재고, 사진 사용 권리 등은 검증 상태로 유지합니다.
