# 가락한상 Google·네이버 검색 연동 / 소유권 인증 현황
작성일: 2026-11-02
대상: https://garakmall.lexid.site/

## 코드 반영 완료 (등록 전 준비)
- 모바일 헤더: 사용자 선택 스크린샷의 로고 및 마스코트, 30년 전통 문구를 리터치해서 WebP로 등록.
- 모바일 하단: 홈 / 매장 / 시세 / 레시피 / 지도 5종 브랜드 맞춤 아이콘과 활성 표시.
- 모바일 홈·매장·레시피 상세 3개 화면 모두 공통 적용.
- 검색: `/robots.txt`, `/sitemap.xml`, 자동 생성기 `tools/generate_public_sitemap.py`.
- 사이트맵: 유효한 공개 페이지 198개, 검색 대상이 아닌 로그인·계정·관리자 제외.
- 사용자별 로그인/장바구니/관리자 파일은 X-Robots-Tag noindex/nofollow.
- 사이트맵 제출이 검색 상위노출이나 색인 등록을 보장하지는 않음.

## Google Search Console: 소유권 인증 및 사이트맵 제출
1. https://search.google.com/search-console 접속 후 실제 사이트 관리 Google 계정으로 로그인.
2. 속성 목록에 `https://garakmall.lexid.site/` (URL 접두어) 또는 도메인 `lexid.site`가 이미 등록돼 있는지 확인.
3. 미등록이면 URL 접두어 속성 추가 후 소유 확인 (HTML 파일/메타태그, DNS TXT 중 선택).
4. 검증용 HTML 파일을 제공받으면 **원본 파일 내용·파일명 그대로** `storefront/<검증파일>.html`로 추가하여 공개 경로 200 확인. 메타태그 방식은 실제 사이트 `<head>`에 값 삽입. 검증 값은 추측하거나 임의 생성하지 않음.
5. 소유 확인 완료 후 색인 > Sitemaps에 `https://garakmall.lexid.site/sitemap.xml` 제출.
6. 제출 결과의 성공/가져올 수 없음 여부 및 색인 생성 보고서 확인.

## 네이버 서치어드바이저: 소유권 인증 및 사이트맵 제출
1. https://searchadvisor.naver.com/console/board 접속 후 네이버 계정으로 로그인.
2. `https://garakmall.lexid.site/`가 소유 확인된 사이트인지 확인.
3. 미확인 시 서치어드바이저가 제공하는 원본 HTML 파일 또는 `naver-site-verification` 메타태그를 받아 실제 정적 HTML에 적용.
4. 네이버 검증기는 JS 주입 메타태그, JS 리다이렉트를 검증하지 않으므로 메타태그는 반드시 정적 HTML `<head>`에 직접 배치.
5. 소유 확인이 완료되면 요청 > 사이트맵 제출에서 `https://garakmall.lexid.site/sitemap.xml` 입력.
6. 웹마스터 도구 사이트 상태 / 수집 / 색인 보고서 확인.
7. 네이버는 사이트 등록 없이 자동 웹수집도 가능하나, 서치어드바이저 등록/소유 확인은 상태 모니터링에 필요.

## 현재 미확인 (성공 주장 금지)
- Google Search Console 계정 내 실제 소유권 인증 여부
- 네이버 서치어드바이저 계정 내 소유권 인증 여부
- 양쪽 콘솔에서 사이트맵 제출 완료 여부
- 색인 생성 성공/검색 결과 노출 여부

연결된 브라우저 컨텍스트가 없어 두 서비스 로그인 세션에 접근하지 못했음. 사용자가 Work 모드의 클라우드 브라우저에서 직접 로그인하면 소유권 인증 및 제출까지 이어갈 수 있음.
로그인 비밀번호·세션 쿠키·OAuth 토큰은 GitHub, ZIP, 채팅에 기록하지 않음.

## 공식 문서
- Google: https://developers.google.com/search/docs/crawling-indexing/sitemaps/build-sitemap
- Google 모바일 URL: https://developers.google.com/search/docs/crawling-indexing/mobile/mobile-sites-mobile-first-indexing
- Naver: https://searchadvisor.naver.com/guide/faq-start-register
