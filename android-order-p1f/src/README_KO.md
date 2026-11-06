# 가락한상오더 Android v1.9 P1E — 인증/실빌드 게이트

**GO-LIVE=NO**, 실제 Google 로그인/주문·결제·배송 불가. 이전 47개 메뉴·이미지/12개 카테고리·장바구니·시연 앱은 유지합니다.

이번 버전: `OAuthLoginFlow.java`(검증된 App Link·공개 클라이언트·Neon 개발 Auth 전부 필수, 일회성 콜백), `verify_debug_apk.py`(실제 aapt/apksigner 검사), `emulator_smoke.py`(실 APK 설치·UI 스모크), GitHub Actions P1E 파이프라인.

로컬 검사:
```sh
python tools/qa_v19_static.py
python -m pytest -q tests/test_mobile_p1.py tests/test_mobile_p16_catalog.py tests/test_mobile_p17_auth.py tests/test_mobile_p18_assetlinks.py tests/test_mobile_p19_apk_gate.py tests/test_mobile_p19_emulator_gate.py
mkdir -p /tmp/gho-p1e-jvm
javac -d /tmp/gho-p1e-jvm app/src/main/java/site/lexid/garakhansang/order/OAuthPkce.java app/src/main/java/site/lexid/garakhansang/order/OAuthCodeExchange.java app/src/main/java/site/lexid/garakhansang/order/OAuthLoginFlow.java tests/jvm/OAuthPkceSelfTest.java tests/jvm/OAuthExchangeSelfTest.java tests/jvm/OAuthLoginFlowSelfTest.java
for test in OAuthPkceSelfTest OAuthExchangeSelfTest OAuthLoginFlowSelfTest; do java -cp /tmp/gho-p1e-jvm "$test"; done
```

**중요:** 실제 APK 빌드/실기기/Google 실로그인은 아직 수행하지 못했습니다. 이번 테스트는 앱 빌드 성공을 증명하지 않습니다. GitHub Actions 워크플로우도 소스 ZIP에 포함된 템플릿이며 원격 GitHub에 커밋/실행되지 않았습니다.

상세: `docs/ANDROID_ORDER_V1_9_P1E_HANDOFF_KO.md`.

---

# 가락한상오더 Android v1.8 P1D — 네이티브 OAuth 교환 보안 준비

- 빌드 대상: Java 네이티브 Android / package `site.lexid.garakhansang.order`, minSdk 26, target/compileSdk 36.
- 브랜드 레드 A, 가락한상 마스코트·47개 데모 상품 이미지·12개 분류·시장→매장→상품 탐색·장바구니·주문서 미리보기는 기존 v1.7에서 유지.
- **GO-LIVE = NO**: 실 사용자 Google 로그인, 실주문, 결제, 주소/배송, 사업자 입점은 비활성.
- 프로젝트 `app/src/main/assets/mobile_api_config.json`은 `enabled=false`, `oauth_enabled=false`, URL/허용 호스트 공란. 실서버 자동 연결 없음.

## v1.8 P1D에서 추가/수정

1. `OAuthCodeExchange.java`: 기존 `OAuthPkce.java`의 **한 번 검증된 콜백 코드**를 Authorization Code + PKCE S256 토큰 교환 요청으로 전환하기 위한 읽기 쉬운 보안 계약. HTTPS·issuer host/path, redirect URI, public client ID, resource, 비밀값 노출 차단; 일회성 코드 교환 준비.
2. `OAuthTokenHttp.java`: HTTP 우회/리디렉션을 허용하지 않는 HTTPS POST 교환 준비 모듈. 응답 JSON 최대 16KB, 응답 타입/수명 검증, 민감 내용 로그 금지. **실제 UI에서 호출하지 않으며 운영 URL·실로그인 설정은 여전히 비활성화**.
3. `tools/generate_assetlinks.py`: 실제 서명 인증서 SHA-256을 입력해야만 `assetlinks.json` 로컬 생성. 미검증 인증서/도메인으로 앱 링크를 표시하지 않음. `docs/ANDROID_APP_LINK_P1D_KO.md` 참고.
4. 마이의 `Google 로그인 준비 상태 (P1D)` 화면에 PKCE 토큰 교환 준비와 Android App Link 미검증 사유 명시.
5. `tests/jvm/OAuthExchangeSelfTest.java`, `tests/test_mobile_p18_assetlinks.py`, `tools/qa_v18_static.py` 추가. CI의 신규 테스트 연결.
6. Gradle `versionCode=18`, `versionName=1.8.0-p1d-oauth-prep` 갱신.

## Neon 실제 개발 환경 확인

- 원래 Neon 프로젝트: `garakhansang` / 프로젝트 ID `mute-darkness-67529424`, `main` 브랜치 `br-ancient-cake-b34e2q55` **미변경**.
- **신규 개발 브랜치:** `dev-garak-order-android-p1d-20261105` / `br-rough-bonus-b33w8dk8`, 부모 `main`의 copy-on-write 개발 스냅샷.
- 새 브랜치는 추가 비용을 줄이기 위해 **no-compute**로 생성: read/write endpoint, Neon Auth, OAuth Provider는 아직 없음. 실제 Google 로그인 E2E 실행 불가.
- 원본 `main` Neon Auth의 Google provider(shared) 설정은 확인됨. 별도 OAuth 2.1 Provider는 비활성화 상태.
- 부모 DB에는 `neon_auth.user=0`, `neon_auth.session=0`, `public.users=5`, `public.orders=5` 확인. 개발 스냅샷에 사용자/주문 레코드가 복제될 수 있으므로 테스트에서 사용·반출하지 말 것. 개인정보 익명화/삭제 SQL 미수행.
- 개발 브랜치에 Auth를 프로비저닝하려 했으나 read/write endpoint 부재로 거절됨. 추가 상시 실행 컴퓨트는 생성하지 않았음.

## 로컬 재현 (Java17, Python3, Pillow/FastAPI/pytest)

```sh
python tools/qa_v18_static.py
python -m pytest -q tests/test_mobile_p1.py tests/test_mobile_p16_catalog.py tests/test_mobile_p17_auth.py tests/test_mobile_p18_assetlinks.py
mkdir -p /tmp/gho-jvm
javac -d /tmp/gho-jvm app/src/main/java/site/lexid/garakhansang/order/OAuthPkce.java app/src/main/java/site/lexid/garakhansang/order/OAuthCodeExchange.java tests/jvm/OAuthPkceSelfTest.java tests/jvm/OAuthExchangeSelfTest.java
java -cp /tmp/gho-jvm OAuthPkceSelfTest
java -cp /tmp/gho-jvm OAuthExchangeSelfTest
```

기존 V5 회귀 테스트는 `_v5_verify/GARAK_HANSANG_ORDER_V5/tests`의 `test_domain.py`, `test_v4_api.py`, `test_v5_auth.py`를 사용.

APK 실빌드: Android Studio SDK36, JDK17, Gradle8.11.1 환경에서 `gradle :app:assembleDebug` 수행 가능하도록 CI 템플릿 포함. **이 세션에 Android SDK/Gradle 및 외부 Gradle 다운로드 네트워크가 없어 아직 빌드하지 못했습니다.** 소스 정적 검사/JVM 보안 검사/pytest 통과와 실제 APK·로그인 성공은 구분합니다.

## 활성화 차단 게이트

1. 서명된 APK/AAB SHA-256, Android Digital Asset Links 웹 배포·실기기 `verified` 상태 확인.
2. Neon 개발 브랜치의 컴퓨트/Neon Auth 준비 후, Google OAuth 로그인·동의 웹 페이지 및 공개 PKCE 클라이언트 등록. 승인된 리디렉션 URL/리소스만 허용.
3. 발급된 실제 access token의 형식, issuer, audience, 서명/JWKS, 권한·만료를 백엔드 검증기로 E2E 확인. 기존 V5 EdDSA JWT와 동일하다고 가정하지 않음.
4. `mobile_api_config.json`을 바꾸거나 앱에 콜백 IntentFilter를 추가하려면 위 검증 결과와 실제 HTTPS 서버가 필요. 초기값은 비활성 유지.
5. 실제 입점상인·상품 승인, 배송권역 검증, 계약, PG 테스트 결제·환불, 실기기 QA 전에는 상용 출시 금지.

기존 Google Drive/GitHub 소스 파일은 수정·삭제하지 않았으며 v1.8은 별도 버전 ZIP입니다.

## P1G 2026-11-06 보완 사항
- 접근성 터치 영역, 카테고리 검색어 리셋, 비동기 응답 경합 차단, 서버 출력 길이 제한 개선.
- v1.10 (20), 실주문·결제·Google 로그인 미연동 · GO-LIVE=NO.
- 인수인계: docs/ANDROID_ORDER_V1_10_P1G_HANDOFF_KO.md


## v1.11 P1H — API/OAuth 응답 검증 강화

- 'HttpResponseGuards' 순수 Java 공통 검사기를 사용해 모바일 카탈로그 API 및 OAuth 토큰 응답의 JSON Content-Type을 **정확하게** 검증합니다. `application/json-unsafe`, charset 혼란, 중복 MIME 파라미터를 거부하며, 모든 JSON은 UTF-8로 파싱합니다.
- OAuth 콜백의 NUL 및 제어문자를 허용하지 않습니다. 일회성 PKCE·state·HTTPS·10분 만료 요건은 유지합니다.
- 실제 APK 서명 검사 시 `apksigner`의 출력에 **v2 이상 서명 확인**이 없으면 성공을 인정하지 않습니다.
- v1.11 / versionCode 21. 테스트: `python tools/qa_v21_static.py`, Python 56건, JVM 102건, V5 47건.
- 원본 47개 AI 참고 메뉴 이미지는 모두 보존, 주문/결제/실제 OAuth 로그인은 비활성.
- **APK 없음**, 운영 DB 수정·상용 배포 없음.
