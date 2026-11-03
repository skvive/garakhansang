# 가락한상 입점·커뮤니티 운영 연동 (2026-11-03)

## 운영 범위
- 기존 운영 네온 DB `dawn-paper-21288363`, 기본 브랜치 `br-jolly-surf-b5wb7ior`
- 기존 Neon Auth 사용, 브라우저 `getJWTToken()` + 서버 JWKS 공개키 검증 (issuer: Neon Auth origin)
- `GET/POST /api/merchant-applications`: 신청 접수, 신청인 본인 목록
- `GET/POST /api/community/posts`: 승인된 공개 글, 회원의 본인 글, 검수 대기 글 접수
- `GET/POST /api/community/comments`: 승인된 게시글 댓글 공개/접수
- `GET/POST /api/community/moderation`: 기존 관리자 세션+CSRF+권한 확인 후 검토/승인/반려
- 관리자 `/admin/` 사이드바 → `/merchant-showcase/moderation.html`
- 입점 신청 검토 완료 ≠ 입점 계약 또는 판매 승인. 현장 업체 5곳은 계속 샘플.

## 보안 및 품질
- 관리자 외 입점 신청 연락처 비공개
- 쿼리 파라미터 바인딩, 입력값 길이/형식, 요청 크기 제한
- 사용자 24시간 신청 3건/글 5건/댓글 20건, 동일 상호 대기 중 재신청 거절
- 승인 전 글과 댓글은 외부 목록에 표시하지 않음
- 클라이언트 글/댓글은 `textContent`로 출력
- 테스트: `python3 -m unittest discover -s tests -p test_merchant_community_api.py -v`
- 정적 검사: `python3 -m py_compile admin_core/merchant_community.py api/index.py`, `node --check storefront/merchant-showcase/assets/merchant-online.mjs`

## 운영자 검증 체크
1. Neon Auth 실제 회원으로 이메일/Google 로그인 → 입점 신청 접수, 신규 신청 번호와 내 이력 확인
2. 관리자 로그인 → 입점 신청 검토함에서 내용 읽기, 검토 완료 상태 확인
3. 회원 게시글 등록 → 관리자 승인 전 공개 목록 미노출, 승인 후 공개
4. 승인 글에 댓글 등록 → 승인 전 비공개, 승인 후 표시
5. 잘못된 토큰/출처/중복 신청/CSRF 실패 테스트
6. 모바일 360/390/768px 및 데스크톱 화면 검수, 오류/실제 전송 여부 확인

## 아직 미구현
- 실제 주문·계약·입점 업체 자격 검증 및 실결제 연동
- 신청자 메일 알림/운영자 자동 알림, 첨부파일
- 정기 개인정보 파기 자동화, 회원 셀프 삭제
- 실사용자 로그인 기반 E2E/브라우저 접속 검증: 실행 권한/보안 로그인 필요
- 개인정보 보관기간, 운영 책임자, 제3자 제공 여부 및 최종 법률 검토 확정 필요
