# 가락한상오더 Android P1G · v1.10 보완본

> **상태: 소스 보완 및 원격 회귀 테스트 완료. APK/Google 실로그인/실결제는 미완료. GO-LIVE=NO.**

## 코드 및 검증
- **개발 브랜치**: `chatgpt/garakhansang-order-android-p1g-20261106`
- v1.9 개발 소스 경로를 보존하며 `android-order-p1f/src/`에 v1.10 개선 코드 반영 (P1F 원본 브랜치 보존)
- 접근성 버튼(48dp), 카테고리 전환 검색어 초기화, 순수 Java 검색 필터, 비동기 응답 순서 차단, 서버 응답 문자열 제어문자·길이 제한
- `.github/workflows/order-android-p1g-source-ci.yml`: Python 52개 + JVM 82개 오프라인 검증 (APK 빌드 아님)
- 47개 상품/12개 카테고리 **판매 불가 상태**, 실제 주소·주문·결제·배송 비활성

## APK 실제 빌드 입력 원본
- **[비공개 Google Drive v1.10 원본 폴더](https://drive.google.com/drive/folders/1TDmliT9Mbk0Uk3v_SsHd3NZAUKnPjsDl)**
- ZIP: `GarakHansang_Order_Android_v1_10_P1G_Source_20261106.zip`
- ZIP bytes: **4762902**, SHA-256: `7a294cfc1f90158280881feab523d47e7b177e1263d86cec96c973470bfe680d`
- 구성: **153개 파일**, 47개 상품 이미지 포함; 이전 v1.9와 미디어 59개 동일
- GitHub 업로드 필요 위치: `android-order-p1g/GarakHansang_Order_Android_v1_10_P1G_Source_20261106.zip`

빌드 전 검증기 `android-order-p1g/tools/verify_source_archive.py`는 정확한 ZIP 해시·153개 파일·47개 이미지를 확인합니다. ZIP이 브랜치에 실제 커밋될 때만 `.github/workflows/order-android-p1g.yml`에서 Android SDK36/Gradle 빌드·debug APK 서명 검사 및 에뮬레이터 설치 검증을 시작합니다. 현 시점 GitHub에 ZIP은 **없으므로 APK 없음**.

## 출시 전 P0 필수
1. GitHub 브랜치에 원본 ZIP을 정확한 파일명으로 업로드하고 APK·에뮬레이터 CI 통과 확인.
2. Android 디버그/출시 서명 SHA-256 확인 후 실제 HTTPS App Link 소유권 및 `assetlinks.json` 검증.
3. 운영 데이터와 분리된 Neon Auth 개발 환경에서 Google OAuth public client 등록, PKCE 로그인·만료·취소 E2E 테스트.
4. 승인된 입점 매장·판매가·재고·배송 가능 권역, 취소·환불·PG/웹훅, 정산, 개인정보·약관의 실서비스 검증.
5. 승인 전에는 **GO-LIVE=NO** 및 실제 주문·결제 차단 유지.

이 PR은 코드 검토용입니다. 위 게이트 통과 전 프로덕션 `main`으로 병합하거나 상용 출시하지 마세요.
