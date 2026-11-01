# 가락한상 Neon Auth 회원 / 마이페이지 — 작업 및 배포 검수

## 실제 연동 확인
- Neon 프로젝트 **dawn-paper-21288363**, 브랜치 **br-jolly-surf-b5wb7ior**.
- 공개 Auth URL은 이미 사이트 \`auth/config.public.json\`과 일치함.
- Neon 관리 인증(provider=better_auth), Google OAuth provider(shared) 등록 확인.
- Auth trusted domain: https://garakmall.lexid.site / https://garakhansang.vercel.app.
- 이메일·비밀번호 사용 및 공개 회원가입 허용 (실제 이메일 발송/Google OAuth 로그인 완료 단계는 사용자 계정의 실제 로그인으로 추가 확인 필요).
- 이 프로젝트의 Neon Data API는 현재 **활성화되지 않음** (get_data_api: 404).
- 기존 \`public.customers\`, \`public.orders\`의 ID는 auth user UUID와 연결되어 있지 않음. 기존 admin test 주문을 사용자 주문으로 표시하면 개인 정보 유출 가능성이 있어 금지.

## 이번 구현
- /login.html: Google 로그인과 이메일 계정의 로그인·회원가입 분리.
- /mypage.html: Auth 세션 검증 후 계정 대시보드, 장바구니, 주문, 배송, 쿠폰, 개인정보(표시 이름) 수정.
- 프로필 이름 변경은 \`auth.updateUser({name})\`으로 Neon Auth에 직접 요청. 서버 확인 후에만 성공 표시.
- 장바구니는 기존 \`garak-hansang-demo-cart\` 브라우저 저장소의 **시연 정보**를 보여줌. 계정에 저장되거나 다른 기기에 동기화되었다고 주장하지 않음.
- 시연 쿠폰: 기존 \`garak-brand-wallet\`의 **로컬 시연 항목** 조회. 발급/실사용 쿠폰 아님.
- 주문·배송: 실제 사용자 UUID와 매핑된 주문 API가 없으므로 **빈 상태**, 다른 사용자 주문 노출 금지.
- 연락처/배송지: 보호된 DB/RLS가 준비되기 전에는 개인 정보를 브라우저에 저장하지 않음.

## 서버 저장 후속 작업 (별도 승인 필요)
- \`db/migrations/20261102_shop_customer_account_rls.sql\`은 **미적용 검토용**.
- Neon Data API를 활성화하고 SQL을 반드시 임시 브랜치에서 먼저 테스트.
- RLS 우회/타인 UUID 조회/인증 없는 쓰기/타인 주문·쿠폰을 접근할 수 없는지 공격 케이스 테스트.
- 통과 후 운영 마이그레이션 적용에 **사용자 명시 승인 필요**.
- 이후 \`@neondatabase/neon-js\` Data API 클라이언트를 Neon Auth JWT + RLS와 연결하여 장바구니/배송지 계정별 저장 활성화.
- 주문·배송/쿠폰은 결제 및 운영 관리자 이벤트에서만 발행하도록 서버 전용 API 구현.
- API 호출 실패/주문 미존재를 가짜 주문으로 채우지 말 것.

## 브라우저 QA
- 세션 모의 테스트(실제 OAuth 자격정보 사용 없음): 360/390/768/1280px 사용자 UI + 비로그인 게이트 5/5 PASS.
- Google OAuth 성공 여부는 **실제 사용자 계정으로 아직 검증하지 않았음**.
- 운영 환경에서 Google 로그인→마이페이지 복귀, 이메일 회원가입/비밀번호 확인, 로그아웃, 프로필 변경 후 재진입을 수동 점검.
- 데스크톱과 모바일 기존 장바구니 페이지는 시연 장바구니라는 상태를 유지.
