# 가락한상 오더 (Garak Hansang Order) — V3 개발 브랜치

한국 전통시장 상인 전용 배달·합배송 시연 앱입니다. 공식 레드 A 오토바이 캐릭터 및 기존 가락한상 브랜딩을 유지합니다.

## 실행

```bash
python backend/server.py --port 8768
```

- 고객: http://127.0.0.1:8768/order/
- 운영: http://127.0.0.1:8768/order/ops.html
- 운영 콘솔에 **로컬 서버 터미널에 표시되는 관리자 토큰**을 입력합니다. 코드를 수정하여 고정 비밀번호를 넣지 마세요.

## 테스트

```bash
python -m unittest discover -s tests -p 'gho_test_domain.py' -v
python tests/gho_http_api_qa.py
```

브라우저 UI 검사는 Playwright와 Chromium이 설치된 로컬 환경에서 `python tests/gho_browser_qa.py`로 실행하며, 브라우저→HTTP 서버의 종단간 테스트가 아니라 Python 도메인 브리지 기반의 렌더링 검사입니다.

## 실제 지원 범위

- 시장별 상품/상인, 서버 가격 검증, 시장별 합배송 견적, 쿠폰 시연, 재고 차감
- 상인 신청/승인, 가상 결제, 점포 준비, 공동집하, 라이더 배정/배송완료 모의 흐름
- 로컬 운영 토큰, 고객별 주문 접근 토큰, Origin 제한
- Neon 개발 브랜치 `dev-garak-hansang-order-20261102`의 `gho` 스키마 적용 검증

**아직 없는 것:** Neon DB에 실제 주문 저장, Neon Auth, 실결제/환불, 위치 추적, Android APK, 운영 배포. 현재 API는 **SQLite 로컬 시연**만 지원합니다.

상세: [V3 인수인계](docs/PHASE3_DEV_HANDOFF.md), [QA](docs/QA_V3.md), [2차 명세서](docs/PHASE2_DEV_SPEC.md).
