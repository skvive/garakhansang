# 가락한상 V9 — GitHub / Vercel / Neon

원팩 `GARAK_HANSANG_CURSOR_ONEPACK_V9`를 `skvive/garakhansang`에 올리고 Vercel(`garakmall.lexid.site`) + Neon Auth(Google)로 배포합니다.

## 로컬 원클릭

```powershell
py -3 tools\onepack.py doctor
INSTALL_AND_RUN_WINDOWS.bat
```

- 쇼핑몰: http://127.0.0.1:8099/
- 관리자: http://127.0.0.1:8099/admin/

## 클라우드

- 정적 스토어프론트: `storefront/`
- API: `api/index.py` → `admin_core` (Neon `DATABASE_URL` 있으면 Postgres, 없으면 SQLite)
- 고객 로그인: Neon Auth Google / 이메일 (`storefront/login.html`)
- 관리자 로그인: `/admin/` + `GARAK_BOOTSTRAP_PASSWORD` 로 만든 `admin` 계정

실결제·실배송은 비활성입니다.
