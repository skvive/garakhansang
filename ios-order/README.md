# 가락한상오더 iOS / iPhone · P1I

**별도 iOS 네이티브 SwiftUI 앱**. Android v1.11의 47개 AI 콘셉트 메뉴 이미지·12개 분류·판매 불가 플래그를 재사용했습니다.

- **사용자용 소스 ZIP**: [비공개 Google Drive v1.0 P1I 백업](https://drive.google.com/drive/folders/1v-JzoLjAZIsSKpWgebmYh5odjqx2ACkR)
- **GitHub 트래킹 가능 Swift 소스**: `ios-order/Sources/` (5개 Swift 파일), Xcode 프로젝트 `ios-order/project.pbxproj`.
- **정확한 원본 소스 ZIP 보관**: `ios-order/source-b64/part-000.txt`~`part-051.txt`. GitHub Actions가 원본 ZIP을 복원하고 SHA-256 및 47개 이미지를 확인한 후 Swift 파일과 Xcode 프로젝트를 반영합니다.
- **ZIP SHA-256**: `02c9094a36edc7f7da06ce0a14c7ccd8982da3537d394f14f1865f1c425facd1` (5,072,001 bytes / 63 entries).
- **워크플로**: `.github/workflows/garakhansang-ios-p1i.yml`. macOS Xcode iOS Simulator 빌드, `.app` 번들/47개 이미지 검증, 시뮬레이터 설치·실행·스크린샷.
- **iOS bundle identifier**: `site.lexid.garakhansang.order.ios`; minimum iOS 16.
- **애플 개발자 서명 미구성**: Simulator .app 아티팩트는 iPhone 설치용 IPA 또는 App Store 제출용 빌드가 아닙니다.

**실제 판매·입점 승인·배달 가능 권역·Google 로그인·Neon 운영 DB·결제·정산 미연동. GO-LIVE = NO.**

Xcode를 사용하는 Mac에서는 ZIP을 받아 `GarakHansangOrder.xcodeproj`를 열면 됩니다. 공식 브랜드 로고와 47개 원본 이미지는 압축파일 안에 있습니다.

## P1I v1.0.1 Simulator installation fix
The original project had a top-level `Resources` folder within the `.app` bundle, which is reserved and can prevent iOS Simulator from recognizing its bundle ID. The verified build workflow now moves it to `GHSContent`, and the tracked Swift/Xcode sources were updated accordingly. The original ZIP is retained as provenance; updated v1.0.1 full source is separately backed up in Drive. Signing remains Simulator-only.


## iOS P4 지도·5화면 QA (2026-11-07)

- 기존 Google Drive P1I v1.0.1 47개 이미지/12개 분류/공식 로고 원본을 변경하지 않았습니다.
- `Sources/VerifiedMarketNavigation.swift`: Garakland 검증 좌표 기준을 복제하여 실제 승인된 매장 위치만 경로 목표로 사용. 시연 상품 및 미검증 매장은 **가락시장 입구**로만 Google Maps 이동.
- `Sources/MainViews.swift`의 메뉴 상세·마이탭에 지도 링크 추가. GPS·고객 주소 권한은 요구하지 않습니다.
- `Tests/VerifiedMarketNavigationTests.swift`: HTTPS/Google 호스트/좌표 검증/시연·이상좌표 거부·여행 모드 등 순수 Swift 정책 테스트.
- `.github/workflows/garakhansang-ios-p4-qa.yml`: macOS Xcode **실제 unsigned iOS Simulator 빌드**, 번들 47이미지·SHA/앱 ID 검사, iPhone simulator 홈·메뉴·장바구니·주문내역·마이 5화면 실행 스크린샷.
- 개발 산출물은 simulator `.app` ZIP만 생성합니다. **iPhone 실기기 설치·TestFlight·App Store용 IPA와는 다르며, Apple Developer Team 인증서·프로비저닝이 필수**입니다.
- 실상품 승인(0/37), Stripe 실계약·테스트 키·환불·배송·Neon Auth 실제 API가 모두 확인되기 전에는 상용 출시 차단을 유지합니다.

검증 기록: https://github.com/skvive/garakhansang/actions/workflows/garakhansang-ios-p4-qa.yml
