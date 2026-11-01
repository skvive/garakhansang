# 가락한상 일별 공식 수산 시세 자동화 (준비 단계)

공식 데이터 기준: KAMIS 서울 수산물 도매 참고가격 (가락시장 고유 경매가 아님).
출처: https://www.kamis.or.kr/customer/reference/openapi_list.do?action=detail&boardno=1

## 자동화 작동 조건
1. KAMIS 가격정보 Open API에서 이용신청 후 cert key/id 발급.
2. GitHub skvive/garakhansang → Settings → Secrets and variables → Actions에 KAMIS_CERT_KEY와 KAMIS_CERT_ID 등록.
3. GitHub Actions enabled, workflow permissions contents:write 확보.
4. 매일 04:10 UTC / 13:10 KST 실행. 수동 workflow_dispatch 가능.
5. 정상이면 storefront/data/seoul-seafood-wholesale-latest.json 갱신 커밋. 실패/미설정/무데이터/단위·날짜 누락이면 기존 파일 불변.
6. 최초 실제 API 호출 및 데이터 검증 후 가격 페이지 UI에 연결. 인증키가 없으므로 현재 실제 가격을 게시하지 않음.

## 엄격한 구분
- 가격 타입: 서울 도매 참고가격(지역=서울, 수산 분류 600, 도매 02).
- 온라인 쇼핑몰의 상인 판매가와 동일하지 않음. 가락시장 개별 경락가격도 아님.
- 시장별 경락가격을 원하면 추가로 data.go.kr/data/15109049/openapi.do 또는 aT 전국 공영도매시장 경매원천정보의 API 키, 시장 코드와 단위 검증이 필요.
- 휴장일에는 발표된 마지막 실거래일로 표기. 기준일과 갱신시각 별도 보관.
- 단위, 등급, 어종/품종을 유지해 잘못된 1kg 환산/가격비교 방지.
- 데이터 활용 시 출처 링크 표시. API 키·인증 아이디는 절대 프런트에 노출하지 않음.
- GitHub 커밋이 Vercel의 새 배포를 일으키는지는 실제 성공 첫 실행 시 확인. GitHub Actions 크론은 정확한 분 단위 실행 보장 없음.

## 테스트
python3 -m unittest tests/test_sync_seafood_wholesale.py

## 가락시장 직접 경매 낙찰가 후속 연동
- 서울시농수산식품공사 경매결과(가락시장): https://www.data.go.kr/data/15076020/openapi.do (API 신청·승인 필요).
- 농림수산식품교육문화정보원 수산물도매시장별도매경락가격조회: https://www.data.go.kr/data/15109049/openapi.do (시장/일자/단위 코드 검증 후 연결).
- 기존 KAMIS API가 반환하는 서울 도매 참고가격을 가락시장 경매 낙찰가격이라고 표기하지 않는다.
- 첫 실데이터 성공·품종/등급/단위 확인 전까지 주기적 갱신이 정상 가동 중이라고 주장하지 않는다.
