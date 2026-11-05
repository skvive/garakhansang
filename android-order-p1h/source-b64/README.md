# Android v1.11 P1H — Verified source transport

This directory contains 98 ASCII Base64 fragments (`part-000.txt` through `part-097.txt`) of the single original private v1.11 source ZIP. The fragments are **only a transport representation** of the verified archive, not independently editable assets.

- ZIP name: `GarakHansang_Order_Android_v1_11_P1H_Source_20261106.zip`
- Expected decoded ZIP size: **4,771,371 bytes**
- Expected ZIP SHA-256: `5508cf1ebac0c84975068bacb7febddb7ae56e7b2a1d51c353fb24e630a1a3d8`
- Original entries: **159**, including **47 menu images**.
- Restore: `cat part-*.txt | base64 --decode > ../GarakHansang_Order_Android_v1_11_P1H_Source_20261106.zip`, followed by SHA-256 and `android-order-p1h/tools/verify_source_archive.py`.

The `.github/workflows/order-android-p1h.yml` GitHub Actions job automatically reconstructs and SHA-validates the ZIP **before** building any Android APK or attempting emulator QA. Production database, checkout, live order capture and Google OAuth remain disabled. **GO-LIVE = NO**.
