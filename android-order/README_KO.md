# 가락한상 오더 Android 네이티브 베타

사용자가 선택한 시안 A(빨간 스쿠터·가락한상 캐릭터)를 앱 아이콘으로 사용합니다. 원본 가락한상 로고는 `app/src/main/assets/garakhansang_official_logo.webp`에 보존합니다.

- 아키텍처: Java Android 네이티브 Activity. WebView 미사용.
- 화면: 홈, 상품 검색·카테고리, 장바구니, 주문준비 안내, 브랜드 소개.
- 실제 기능: 상품 필터·검색, 장바구니 수량 저장, 뒤로가기, 화면 탐색, 오프라인 사진 표시.
- 제한: **실제 주문·결제·배송·가격·재고·판매자 연결은 제공하지 않습니다.** 상품명은 시범 데이터입니다.
- 실제 주문 활성화 전 필요: 입점사업자 동의, 주문 API, 서버 권한, 상품 가격 및 재고, 결제, 취소·환불, 개인정보·약관.

## 빌드
Android Studio에서 이 폴더를 연 뒤 Android SDK 36, JDK 17, AGP 8.10.1, Gradle 8.11.1로 빌드하거나 GitHub Actions를 사용합니다.

- `gradle :app:assembleDebug`
- APK 예상 경로: `app/build/outputs/apk/debug/app-debug.apk`
- Google Play용 AAB와 출시 서명은 별도로 필요합니다.

## 검증 분리
- 소스 검사 및 이미지 디코딩 = 정적 검증
- CI 실제 컴파일 = 빌드 검증
- Android 에뮬레이터 설치 + UI 접근 = 에뮬레이터 검증
- USB 실기기 설치 및 실행 = 별도 실기기 검증

비밀키와 운영 계정은 패키지에 포함하지 않습니다.
