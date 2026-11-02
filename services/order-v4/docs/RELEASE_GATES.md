# 납품 전 비판적 검수 · V4 → 상용 전환 GO/STOP

| 분야 | 확인한 사실 | 판정 |
|---|---|---|
| 시장 특화 | 5개 시장·17종 시연 상품·합배송 시장별 분리 | 로컬/개발 DB 시연 GO |
| Neon | 개발 브랜치 실제 주문 생성·조회·취소·재고 복구 | 개발 DB GO |
| 비즈니스 정확성 | 손질 옵션·냉장 추가 배송·타시장별 별도 주문 | 시연 GO, 실제 요율 계약 필요 |
| 중복·재고 | PostgreSQL 잠금·멱등성, 초과 재고 차단 | 기능 GO, 동시부하 테스트 필요 |
| 인증 | JWT RS256 issuer/audience/expiry/JWKS 검증 구현 | 실제 공급자 설정 전 STOP |
| 상인·기사 | DB 멤버십·권한·상태 전환 검증 구현 | 실계정 검증 전 STOP |
| PG | 실제 결제 및 환불 없음, `demo-authorize`만 지원 | 상용 STOP |
| 개인정보 | 고객 배송주소 저장·라이더 GPS 미구현 | 상용 STOP |
| 보안 | DB owner가 RLS 우회, 별도 최소권한 role/grant 미검증 | 인터넷 공개 STOP |
| API 연동 | psycopg 드라이버 현재 환경에 미설치, HTTP→Neon 미검증 | 상용 STOP |
| UI | 기존 V3 레드 A 마스코트·고객 PWA 및 운영 콘솔 보존, V4 새 UI 실기기 렌더링 미검증 | V4 디자인 납품 STOP |
| Android | APK 빌드·실기기 설치 미수행 | Android 배포 STOP |

**출시 판단: STOP(상용화), GO(격리 개발 단계).**
