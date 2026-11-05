# Garak Hansang Order Android P1F — verifiable v1.9 build source

This isolated development branch does not modify production `main`.

## Source of truth
- Source archive: `android-order-p1f/source-parts/part-000.b64` through `part-024.b64`, each containing a base64-encoded sequential segment of **GarakHansang_Order_Android_v1_9_P1E_Source_20261105.zip**.
- Archive SHA-256: `5c3c03ab5412e6aec03dc489f3a55d36d48d1baa6339370c84f83ac1e2741f7e`.
- Original archive size: **4,754,258 bytes**; **147 files**, including the existing 47 menu images.
- Original private Google Drive backup: https://drive.google.com/file/d/1AsXu_zJBFRWj-8Tp1M-yNY9YONg0_p6O/view

## Build
The branch's `.github/workflows/order-android-p1f.yml` reconstructs the original ZIP, verifies its SHA-256, unpacks it into a temporary project, runs Python and Java security/contract tests, builds and verifies an actual debug APK, and runs an Android emulator smoke test. Any missing/mismatched chunk or APK signature fails the job.

The older `android-order/` tree on the base branch is an earlier prototype and **does not contain the v1.9 47-image catalog**. Do not build it as P1F; use the workflow's verified ZIP only.

## Security
Demo only. Google OAuth login, live Neon access, real payment, order acceptance, and rider dispatch remain disabled. The debug certificate fingerprint cannot by itself establish Android App Link domain ownership. Do not release commercially from this workflow.

Never upload private API secrets, signing keys, or personal customer data into the repository.