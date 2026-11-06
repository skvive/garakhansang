# 가락한상 오더 · iPhone 네이티브 데모 (iOS 0.1.0)

**Android v1.11 P1H 원본 기반 SwiftUI/Xcode 프로젝트.** 기존 브랜드·캐릭터·가락시장 30년 전통의 맛 문구와 47개 사용자 제공 상품 자료를 재사용했습니다. iOS 버전은 기존 Android 데모와 동일하게 **GO-LIVE=NO**이며 주문·결제·로그인·배송은 차단했습니다.

## 구현 기능
- iPhone/iPad SwiftUI 네이티브 화면: 홈, 찜, 장바구니, 마이 (4개 탭)
- 47개 메뉴·12개 분류, 검색, 카테고리 전환 시 이전 검색어 초기화
- 상품 AI 콘셉트 이미지·상세 설명·참고 가격 표시
- 로컬 찜, 수량 제한(메뉴당 20개)의 **미리보기 장바구니**, 배달/포장 UI (실제 주문 불가능)
- iOS VoiceOver 라벨·44pt 이상 버튼·동적 텍스트·원본 브랜드 팔레트
- Android의 원본 `catalog/menus_47.json`과 동일한 JSON 자료를 사용
- 위치·연락처·결제·OAuth 토큰을 수집/전송하지 않음

## 설치 및 테스트
1. macOS + Xcode 16 이상에서 `GarakHansangOrder.xcodeproj`를 엽니다.
2. `GarakHansangOrder` scheme을 선택하고 iOS 16 이상 iPhone 시뮬레이터에서 실행합니다.
3. **본 ZIP에 포함된 `Assets.xcassets`는 이미 채워져 있습니다.** 이미지가 없거나 iOS 소스를 GitHub만 받은 경우, 아래 `hydrate_assets.py`를 실행하세요.
4. 실제 iPhone에 설치하려면 본인의 **Apple Developer Team과 코드 서명**을 설정해야 합니다. 이 ZIP에는 서명 키/프로비저닝 정보가 없습니다.

```bash
python3 -m pip install Pillow
python3 Tools/hydrate_assets.py --source-zip /path/to/GarakHansang_Order_Android_v1_11_P1H_Source_20261106.zip --project .
python3 Tools/check_project.py
swift test --parallel
xcodebuild -project GarakHansangOrder.xcodeproj -scheme GarakHansangOrder -configuration Debug -destination 'generic/platform=iOS Simulator' CODE_SIGNING_ALLOWED=NO build
```

**GitHub CI**는 기존 `skvive/garakhansang`의 별도 Android P1H 개발 브랜치에 이미 보관된 원본 ZIP Base64 조각 98개를 병합해 SHA-256을 확인하고, 47개 메뉴 이미지를 생성한 뒤 macOS에서 Xcode 빌드를 검증합니다. GitHub iOS 소스 폴더에는 바이너리 이미지 중복 저장을 피했습니다.

## 로그인·결제 제한
Neon Auth 개발 OAuth 클라이언트, Apple universal links, Google 로그인/Apple 로그인, 매장 승인·재고·가격·배송권역·PG 계약·취소/환불/정산은 미구현입니다. 이 단계에서는 Apple 앱 심사·TestFlight·실기기 배포가 불가하며, **macOS Xcode에서 서명 확인 후 별도 진행**해야 합니다.

## 원본 소스 보존
- Android v1.11 ZIP SHA-256: `5508cf1ebac0c84975068bacb7febddb7ae56e7b2a1d51c353fb24e630a1a3d8`
- `Shared/Resources/menu_catalog.json`은 기존 `catalog/menus_47.json` 원문 바이트 복제
- `Assets.xcassets`는 원본 메뉴 JPEG와 기존 `garakhansang_official_logo.webp` / `order_brand_512.webp`에서 생성; AI로 새 로고를 만들지 않음
- 원본은 변경·삭제하지 않으며 출시 전 수동 디자인·실제 서비스 QA 필요
