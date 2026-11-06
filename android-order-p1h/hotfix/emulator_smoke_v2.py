#!/usr/bin/env python3
"""Fail-closed native Android emulator QA, with screen evidence and semantic navigation.

Checks genuine APK install, foreground process, accessibility tab controls and unique
page content. Never triggers live payment, orders or login.
"""
import argparse
import re
import subprocess
import time
import xml.etree.ElementTree as ET
from pathlib import Path

PACKAGE = "site.lexid.garakhansang.order"
ACTIVITY = PACKAGE + "/.MainActivity"
TABS = (
    ("메뉴", "products", "상품 탐색"),
    ("장바구니", "cart", "선택한 상품을 확인하세요"),
    ("주문내역", "orders", "실제 주문 서버 미연동"),
    ("마이", "my", "마이 가락한상"),
)


def adb(*args, output=False, check=True):
    cmd = ["adb", *args]
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, timeout=60)
    if check and p.returncode:
        raise RuntimeError(f"adb failed ({p.returncode}): {args!r}: {p.stderr.decode(errors='replace')[-500:]}")
    return p.stdout.decode("utf-8", errors="replace") if output else p.returncode


def bounds_center(value):
    match = re.fullmatch(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", value or "")
    if not match:
        raise ValueError("Invalid accessibility bounds")
    x1, y1, x2, y2 = (int(g) for g in match.groups())
    if x2 <= x1 or y2 <= y1:
        raise ValueError("Non-positive accessibility bounds")
    return ((x1 + x2) // 2, (y1 + y2) // 2)


def nodes(xml):
    return list(ET.fromstring(xml).iter("node"))


def visible_strings(xml):
    return [n.attrib.get(k, "") for n in nodes(xml) for k in ("text", "content-desc") if n.attrib.get(k)]


def nav_center(xml, label):
    wanted = label + " 탭"
    for n in nodes(xml):
        if n.attrib.get("content-desc") == wanted and n.attrib.get("bounds"):
            return bounds_center(n.attrib["bounds"])
    for n in nodes(xml):
        if n.attrib.get("text") == label and n.attrib.get("bounds"):
            return bounds_center(n.attrib["bounds"])
    raise ValueError(f"No accessible navigation target: {label}")


def ui_xml():
    adb("shell", "uiautomator", "dump", "/sdcard/gh-order-ui.xml")
    raw = adb("shell", "cat", "/sdcard/gh-order-ui.xml", output=True)
    ET.fromstring(raw)
    return raw


def wait_screen(marker=None, timeout=20):
    last = ""
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if not adb("shell", "pidof", PACKAGE, check=False) == 0:
            raise RuntimeError("Native app terminated before screen verification")
        try:
            data = ui_xml()
            last = data
            values = visible_strings(data)
            tabs = sum(1 for label, _, _ in TABS if any(x == label + " 탭" or x == label for x in values))
            app_nodes = sum(1 for n in nodes(data) if n.attrib.get("package") == PACKAGE)
            if tabs >= 3 and app_nodes >= 4 and (marker is None or any(marker in x for x in values)):
                return data
        except (RuntimeError, ValueError, ET.ParseError):
            pass
        time.sleep(1)
    details = " ".join(visible_strings(last)[:35]) if last else "no UI XML"
    raise RuntimeError(f"UI did not expose expected tabs/page {marker!r}: {details[:900]}")


def screenshot(path):
    with path.open("wb") as out:
        subprocess.run(["adb", "exec-out", "screencap", "-p"],
                       stdout=out, check=True, timeout=40)
    if path.stat().st_size < 5000:
        raise RuntimeError(f"Screen capture is empty: {path.name}")


def record(tag, xml, out):
    (out / (tag + ".xml")).write_text(xml, encoding="utf-8")
    screenshot(out / (tag + ".png"))


def run(apk, out):
    if not apk.is_file() or apk.stat().st_size < 10000:
        raise RuntimeError("Actual APK artifact not found")
    out.mkdir(parents=True, exist_ok=True)
    try:
        adb("install", "-r", str(apk))
        adb("shell", "am", "force-stop", PACKAGE)
        adb("shell", "am", "start", "-W", "-n", ACTIVITY)
        home = wait_screen(marker=None)
        record("home", home, out)
        for name, dest, unique in TABS:
            xy = nav_center(home, name)
            adb("shell", "input", "tap", str(xy[0]), str(xy[1]))
            view = wait_screen(marker=unique)
            record(dest, view, out)
            home = view
        print("PASS: genuine signed APK installed and 4 accessible tabs navigated.")
    except Exception:
        try:
            screenshot(out / "failure.png")
            (out / "failure-state.txt").write_text(
                adb("shell", "dumpsys", "activity", "activities", output=True)[-20000:],
                encoding="utf-8",
            )
        except Exception:
            pass
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--apk", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    run(args.apk, args.out)
