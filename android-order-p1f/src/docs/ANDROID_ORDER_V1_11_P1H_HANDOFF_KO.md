# 가락한상오더 Android v1.11 P1H · 보안 강화 인수인계

## 변경 범위
- GitHub P1G 개발 브랜치 및 운영 main은 보존. v1.11은 독립 P1H 코드 검토·정적 QA 용도.
- `app/src/main/java/.../HttpResponseGuards.java`: 모바일 API/OAuth 공통으로 응답 Content-Type `application/json[; charset=UTF-8]`만 수락. 잘못된 MIME·다중/미승인 charset 거부.
- `OAuthPkce.java`, `OAuthCodeExchange.java`: OAuth 콜백 코드에서 NUL/DEL 포함 ISO 제어문자 거부.
- `tools/verify_debug_apk.py`: 실제 `apksigner`로 확인된 v2 이상 서명 필수. v21, minSdk26, targetSdk36, 패키지/해시 확인.
- `app/build.gradle.kts`: versionCode=21 / versionName=1.11.0-p1h-http-safety-demo.
- `tests/jvm/HttpResponseGuardsSelfTest.java`, `tests/test_mobile_p1h_security.py`, `tests/test_mobile_p19_apk_gate.py`: MIME/서명/코드 보안 회귀 검증 확대.
- `tools/qa_v21_static.py`: 신규 정적 QA, 기존 v20 QA 소스와 기준 대장 보존.

## 회귀 검증
- Python API/UI 및 보안 테스트 56개, JVM PKCE/OAuth/검색/MIME 총 102개, V5 테스트 47개.
- 47개 이미지·12개 분류 등 기존 카탈로그 보존, 실제 주문·배송·결제 비활성.

## 남은 P0/P1
1. GitHub 독립 브랜치에 v1.11 **전체 이미지 포함 ZIP** 등록 후 정확한 해시 검증 → Android SDK36/Gradle8.11.1 실제 debug APK 빌드·서명/에뮬레이터 QA.
2. Neon Auth 개발 브랜치 컴퓨트/인증 설정, Google public OAuth client, HTTPS App Link 소유권과 Android 서명 지문 검증. 실제 로그인 취소/만료/재시도 E2E.
3. 매장 승인·상품 가격/원산지/재고·배송권역·PG/취소환불·배차·정산 운영 데이터 검증.
4. 서명된 릴리스 AAB, Google Play 정책·개인정보 약관 및 단말 UI 접근성 검사.

**GO-LIVE = NO**. 미검증 성공 주장 금지. 비밀 키/실사용자 정보 저장 금지.
