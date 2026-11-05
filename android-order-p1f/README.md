# 가락한상오더 Android P1F — v1.9 APK 빌드 브랜치

**상태: GitHub 브랜치와 CI/검증기 반영 완료. v1.9 소스 ZIP은 아직 이 브랜치에 업로드되지 않았으며 APK 빌드는 실행되지 않았음.** 기존 운영 `main` 및 이전 소스는 변경하지 않았습니다.

## P1F 진행 현황 (2026-11-06)
- **v1.9 텍스트 소스 36개를 `android-order-p1f/src/`에 별도 커밋**: MainActivity, API, OAuth, 카탈로그 JSON, Gradle 설정, 오프라인 단위테스트·QA 도구. 원본 4개 핵심 소스의 Git blob SHA가 v1.9 ZIP과 일치합니다.
- **GitHub 원본 해시 검증**: 텍스트 소스 **36/36개**가 v1.9 ZIP의 Git blob SHA-1과 일치함을 확인했습니다. 임시 전송 폴더는 검증 후 삭제했으며, 원본 ZIP은 보존했습니다.
- **원격 실행 성공**: [Source and OAuth Tests GitHub Actions #42093188290](https://github.com/skvive/garakhansang/actions/runs/42093188290) — Python 46/46, OAuth JVM 66/66. **APK 빌드 아님**.
- **텍스트 전용 CI**: `.github/workflows/order-android-p1f-source-ci.yml`. 오프라인 모바일 API 46개와 OAuth JVM 66개 검증용. Android APK를 만드는 워크플로가 아닙니다.
- **원본 메뉴 이미지 47개와 리소스 아이콘 PNG는 아직 v1.9 전체 ZIP으로만 보관**돼 있으며, 새 GitHub 텍스트 소스 디렉터리에는 포함되지 않습니다.
- 실제 APK 빌드용 `order-android-p1f.yml`은 아래 원본 ZIP이 지정 경로에 커밋돼야 실행되며, 진행 전까지 **GO-LIVE = NO**입니다.

## 원본 및 무결성
- 원본 ZIP: `GarakHansang_Order_Android_v1_9_P1E_Source_20261105.zip` (4,754,258바이트)
- SHA-256: `5c3c03ab5412e6aec03dc489f3a55d36d48d1baa6339370c84f83ac1e2741f7e`
- 원본 구성: 147개 파일 / 47개 메뉴 이미지 포함
- 확인된 [비공개 Google Drive 원본](https://drive.google.com/file/d/1AsXu_zJBFRWj-8Tp1M-yNY9YONg0_p6O/view)
- GitHub에 필요한 업로드 위치: `android-order-p1f/GarakHansang_Order_Android_v1_9_P1E_Source_20261105.zip`

## 이미 반영된 항목
- `.github/workflows/order-android-p1f.yml`: 위 ZIP이 새로 추가되는 push에만 반응하는 빌드/에뮬레이터 파이프라인
- `android-order-p1f/tools/verify_source_archive.py`: 원본 SHA-256, 바이트 수, 압축 파일 수, 파일 경로와 47개 메뉴 이미지 검사 후에만 추출

## ZIP이 준비됐을 때의 다음 절차
1. GitHub 저장소에서 **이 P1F 브랜치**를 선택해 `android-order-p1f/`로 이동합니다.
2. Add file → Upload files로 **위 정확한 이름의 ZIP**을 넣고 해당 브랜치에 커밋합니다. 실사용자 정보·결제비밀키·개인 서명키는 포함하지 마세요.
3. Actions에서 `Garak Hansang Order Android P1F - Verified v1.9 APK` 실행이 생성되는지 확인합니다.
4. 성공한 경우 Actions 아티팩트 `GarakHansang-Order-v19-debug-apk`의 APK·서명 검증 JSON·SHA256을 내려받고, 에뮬레이터 화면 검증까지 확인합니다.
5. 실패했다면 Logs에 나온 문제를 해결하기 전에는 APK 성공이나 상용 출시를 주장하지 않습니다.

이전 `android-order/` 디렉터리는 47개 메뉴 이미지가 없는 과거 실험 버전입니다. P1F는 ZIP 안의 v1.9 프로젝트만 빌드합니다.

## 보안과 출시
Google 실로그인, Neon 운영 API, PG 결제, 실제 주문·배송·정산은 아직 비활성화입니다. **GO-LIVE = NO**. 디버그 서명은 Google Play 출시 서명 또는 App Link 소유권 검증을 대체하지 않습니다.

**전송 한계:** 이 세션의 Drive→GitHub 원본 ZIP 직접 업로드는 연결에서 차단됐습니다. 이 문서의 경로에 ZIP을 실제 업로드하기 전까지 CI 자동 빌드는 시작되지 않습니다.
