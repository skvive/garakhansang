# Android v1.10 P1G — 보완·검증 인수인계

## 개선 완료 (소스)
- 실제 Android Button 기반 버튼 의미·48dp 최소 터치 영역 개선. 상품 카드 찜·추가, 수량 +/- 및 카테고리 필터 높이 정비.
- 시장/매장/상품 필터의 검색어 잔류 해결, 80자 검색 제한, 검색 결과 없음에서 전체보기 제공. 순수 Java 검색 필터와 JVM 테스트 추가.
- 주소·인증·API·시장 조회의 비동기 응답 시퀀스 무효화. 화면이 바뀌거나 Activity가 파괴되면 늦게 도착한 응답을 무시.
- 서버가 전달한 매장·시장·상품 제목의 제어문자 제거와 길이 제한; 읽기 전용 HTTPS JSON MIME 엄격 검사.
- versionCode=20, versionName=1.10.0-p1g-accessibility-demo. 기존 47개 상품/브랜드 이미지와 원본 v1.9은 보존.
- 주문·결제·배달·실제 Google 로그인 비활성, GO-LIVE = NO.

## 검증 범위
- Python API 기존 회귀 테스트, 신규 P1G UI 정적 테스트, 새 JVM 검색 필터 테스트, v1.10 정적 QA 통과 여부 확인 필요.
- 실제 Android SDK/Gradle 빌드·APK·실기기·Neon E2E는 별도 검증. GitHub에 이미지 47개 업로드 미완료이면 APK 성공 주장 금지.
