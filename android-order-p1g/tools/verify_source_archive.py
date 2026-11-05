#!/usr/bin/env python3
"""Fail-closed v1.10 P1G source archive integrity verifier for GitHub Actions."""
import argparse
import hashlib
import stat
import zipfile
from pathlib import Path, PurePosixPath

EXPECTED_SHA256 = '7a294cfc1f90158280881feab523d47e7b177e1263d86cec96c973470bfe680d'
EXPECTED_BYTES = 4762902
EXPECTED_FILES = 153
MAX_UNCOMPRESSED_BYTES = 64 * 1024 * 1024


def verify_and_extract(archive: Path, extract_dir: Path):
    if not archive.is_file() or archive.stat().st_size != EXPECTED_BYTES:
        raise ValueError('Exact P1G source archive is required')
    digest = hashlib.sha256()
    with archive.open('rb') as inp:
        for block in iter(lambda: inp.read(1024 * 1024), b''):
            digest.update(block)
    if digest.hexdigest() != EXPECTED_SHA256:
        raise ValueError('P1G source archive SHA-256 mismatch')
    with zipfile.ZipFile(archive) as z:
        members = z.infolist()
        paths = [x.filename for x in members]
        if len(paths) != EXPECTED_FILES or len(set(paths)) != EXPECTED_FILES:
            raise ValueError('P1G source archive has missing or repeated paths')
        if sum(x.file_size for x in members) > MAX_UNCOMPRESSED_BYTES:
            raise ValueError('Excessive uncompressed source archive size')
        for member in members:
            p = PurePosixPath(member.filename)
            file_mode = member.external_attr >> 16
            if (p.is_absolute() or '..' in p.parts or not p.parts
                    or '\\' in member.filename or stat.S_IFMT(file_mode) == stat.S_IFLNK):
                raise ValueError('Unsafe source ZIP member')
        required = {
            'settings.gradle.kts', 'build.gradle.kts', 'app/build.gradle.kts',
            'app/src/main/AndroidManifest.xml',
            'app/src/main/java/site/lexid/garakhansang/order/CatalogFilters.java',
            'tools/qa_v20_static.py', 'tools/verify_debug_apk.py',
            'tools/emulator_smoke.py', 'tests/test_mobile_p1g_regressions.py',
            'tests/jvm/CatalogFiltersSelfTest.java',
        }
        required |= {f'app/src/main/assets/menu_{i:02d}.jpg' for i in range(1, 48)}
        if not required.issubset(set(paths)):
            raise ValueError('Required Android source, test or 47 menu images missing')
        if z.testzip() is not None:
            raise ValueError('CRC check failed')
        extract_dir.mkdir(parents=True, exist_ok=True)
        z.extractall(extract_dir)
    print('P1G verified: 153 files, 47 original image paths, strict source SHA-256')


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--archive', type=Path, required=True)
    p.add_argument('--extract-dir', type=Path, required=True)
    a = p.parse_args()
    verify_and_extract(a.archive, a.extract_dir)