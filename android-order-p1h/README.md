# 가락한상오더 Android v1.11 P1H — 보안 강화 / APK 대기
**상태: 소스 보안 개선 및 원격 회귀 테스트 통과. APK는 아직 빌드되지 않았으며 GO-LIVE = NO.**

## 검증된 내용
- v1.10 153개 원본 파일 보존, P1H 전체 ZIP **159개 파일**, 원본 **47개 메뉴 이미지** 및 이전 이미지 58개 해시 일치
- `versionCode=21`, `versionName=1.11.0-p1h-http-safety-demo`
- 서버 카탈로그 및 OAuth 토큰 응답의 엄격한 UTF-8 JSON Content-Type 검사
- OAuth authorization code 제어문자 거부, 실제 APK 서명 v2 이상 필수
- [소스 전용 GitHub Actions 성공](https://github.com/skvive/garakhansang/actions/runs/42129280191) — Python **56/56**, Java **102/102**
- 로컬 V5 서버 47개 회귀 테스트, 오프라인 정적 QA 42개 통과
- [v1.11 Google Drive 원본 전체 ZIP/보고서](https://drive.google.com/drive/folders/19Wx_qHVVnjzmkrKRdHvr_lVuByAsEeX7)

## APK 빌드 게이트 — 아직 미실행
원본 전체 소스 ZIP `GarakHansang_Order_Android_v1_11_P1H_Source_20261106.zip`을 이 브랜치의 `android-order-p1h/`에 **정확한 파일명**으로 커밋해야 합니다. SHA-256:
`5508cf1ebac0c84975068bacb7febddb7ae56e7b2a1d51c353fb24e630a1a3d8`

- `.github/workflows/order-android-p1h.yml`은 압축 원본을 검증하고 난 뒤에만 SDK36/Gradle8.11.1 빌드·APK 서명·에뮬레이터 검사를 실행합니다.
- `android-order-p1h/tools/verify_source_archive.py`는 159개 파일, 47개 메뉴 이미지를 검증하며, 없는 ZIP·불일치 해시·압축 오류를 거부합니다.
- 원본 ZIP의 GitHub 대용량 전송은 연결 제약으로 미완료. Drive 백업 및 기존 브랜치는 보존.
- 정확한 실제 APK가 나오기 전 **APK 빌드 성공·실기기 QA·Google 로그인 E2E 통과를 주장하지 않습니다**.

## 운영 금지
Google 로그인 공개, Neon 운영DB 변경, 판매 승인, 주문·결제·배차·정산 활성화 금지. HTTPS App Links/서명/실서비스 결제 계약 확인 전 프로덕션 `main`으로 병합 금지.
