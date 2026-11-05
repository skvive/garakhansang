#!/usr/bin/env python3
"""Fail-closed verification of the archived Android v1.9 source before CI builds."""
import argparse
import hashlib
import stat
import zipfile
from pathlib import Path, PurePosixPath

EXPECTED_SHA256 = "5c3c03ab5412e6aec03dc489f3a55d36d48d1baa6339370c84f83ac1e2741f7e"
EXPECTED_BYTES = 4754258
EXPECTED_FILES = 147


def verify_and_extract(archive: Path, output: Path):
    if not archive.is_file() or archive.stat().st_size != EXPECTED_BYTES:
        raise ValueError("Required v1.9 source archive missing or unexpected byte count")
    digest = hashlib.sha256()
    with archive.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    if digest.hexdigest() != EXPECTED_SHA256:
        raise ValueError("Source archive SHA-256 mismatch")
    with zipfile.ZipFile(archive) as z:
        infos = z.infolist()
        paths = [info.filename for info in infos]
        if len(paths) != EXPECTED_FILES or len(paths) != len(set(paths)):
            raise ValueError("Missing or duplicate archive files")
        for info in infos:
            p = PurePosixPath(info.filename)
            mode = info.external_attr >> 16
            if p.is_absolute() or ".." in p.parts or not p.parts or stat.S_IFMT(mode) == stat.S_IFLNK:
                raise ValueError("Unsafe archive member")
        required = {
            "settings.gradle.kts", "build.gradle.kts", "app/build.gradle.kts",
            "app/src/main/AndroidManifest.xml",
            "tools/qa_v19_static.py", "tools/verify_debug_apk.py",
            "tools/emulator_smoke.py", "requirements-dev.txt",
        }
        required.update(f"app/src/main/assets/menu_{i:02d}.jpg" for i in range(1, 48))
        if not required.issubset(set(paths)):
            raise ValueError("Required source or 47 image assets missing")
        damaged = z.testzip()
        if damaged:
            raise ValueError("Corrupt ZIP entry: " + damaged)
        output.mkdir(parents=True, exist_ok=True)
        z.extractall(output)
    print("Verified v1.9 ZIP SHA-256, 147 entries, 47 images and safe paths.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--extract-dir", type=Path, required=True)
    args = parser.parse_args()
    verify_and_extract(args.archive, args.extract_dir)
