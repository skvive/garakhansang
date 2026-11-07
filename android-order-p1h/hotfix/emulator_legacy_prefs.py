#!/usr/bin/env python3
"""Verify Android launch survives older/wrong-typed demo preferences, without deleting data."""
import argparse
import subprocess
from pathlib import Path
from emulator_smoke_p1j import P, adb, screen

LEGACY_XML = """<?xml version='1.0' encoding='utf-8' standalone='yes' ?>
<map>
    <string name="q0">legacy-cart-string</string>
    <string name="fav0">legacy-favorite-string</string>
    <string name="demo_area_index">wrong-area-type</string>
    <int name="fulfillment" value="1" />
    <int name="q1" value="2" />
</map>
"""

def main(output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    adb('shell', 'am', 'force-stop', P)
    # Debug signed APK enables run-as; edit only this test app's own prefs XML.
    result = subprocess.run(
        ['adb', 'shell', 'run-as', P, 'sh', '-c', 'cat > shared_prefs/order_preview.xml'],
        input=LEGACY_XML.encode('utf-8'), capture_output=True, timeout=30,
        check=False)
    if result.returncode != 0:
        raise RuntimeError('Failed to seed invalid legacy prefs: ' +
                           result.stderr.decode('utf-8', 'replace')[-500:])
    adb('shell', 'am', 'start', '-W', '-n', P + '/.MainActivity')
    screen(output, 'legacy-pref-startup', '가락한상')
    _, pid = adb('shell', 'pidof', P)
    if not pid.strip():
        raise RuntimeError('Legacy preferences caused an immediate app exit')
    print('PASS: corrupt legacy demo preference types did not crash Android startup')

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    main(args.out)
