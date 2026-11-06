#!/usr/bin/env python3
"""Hydrate 47 official-source demo menu JPEGs and brand symbols from a SHA-pinned ZIP.
This program does not generate, replace, or reinterpret any brand artwork.
"""
import argparse, hashlib, io, json, re, zipfile
from pathlib import Path
from PIL import Image

SHA256 = "5508cf1ebac0c84975068bacb7febddb7ae56e7b2a1d51c353fb24e630a1a3d8"
ZIP_BYTES = 4771371


def save_imageset(root: Path, name: str, data: bytes, ext: str):
    folder = root / f"{name}.imageset"
    folder.mkdir(parents=True, exist_ok=True)
    filename = f"{name}.{ext}"
    (folder / filename).write_bytes(data)
    (folder / "Contents.json").write_text(json.dumps({
        "images": [{"filename": filename, "idiom": "universal"}],
        "info": {"author": "xcode", "version": 1}
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf8")


def hydrate(source: Path, project: Path):
    assert source.is_file() and source.stat().st_size == ZIP_BYTES, "Source ZIP missing/wrong byte length"
    assert hashlib.file_digest(source.open("rb"), "sha256").hexdigest() == SHA256, "Source ZIP SHA-256 mismatch"
    with zipfile.ZipFile(source) as z:
        assert len(z.namelist()) == 159 and not z.testzip(), "Corrupt/incomplete original archive"
        catalog = json.loads(z.read("catalog/menus_47.json"))
        assert catalog["not_for_live_sales"] is True and len(catalog["items"]) == 47
        assert all(i["is_orderable"] is False and i["image_is_ai_concept"] is True for i in catalog["items"])
        target = project / "GarakHansangOrder" / "Assets.xcassets"
        target.mkdir(parents=True, exist_ok=True)
        (target / "Contents.json").write_text('{"info":{"author":"xcode","version":1}}\n', encoding="utf8")
        names = set()
        hashes = {}
        for i in range(1, 48):
            name = f"menu_{i:02d}"
            data = z.read(f"app/src/main/assets/{name}.jpg")
            assert len(data) > 1000 and data[:3] == b"\xff\xd8\xff", name
            Image.open(io.BytesIO(data)).verify()
            save_imageset(target, name, data, "jpg")
            hashes[name] = hashlib.sha256(data).hexdigest()
            names.add(name)
        assert set(i["image"][:-4] for i in catalog["items"]) == names
        raw_logo = z.read("app/src/main/assets/garakhansang_official_logo.webp")
        raw_icon = z.read("app/src/main/assets/order_brand_512.webp")
        raw_food = z.read("app/src/main/assets/food.webp")
        for label, raw in [("OfficialLogo", raw_logo), ("FeatureFood", raw_food)]:
            im = Image.open(io.BytesIO(raw)).convert("RGB")
            bio = io.BytesIO(); im.save(bio, format="PNG")
            save_imageset(target, label, bio.getvalue(), "png")
        app_icon = Image.open(io.BytesIO(raw_icon)).convert("RGB").resize((1024,1024), Image.Resampling.LANCZOS)
        folder = target / "AppIcon.appiconset"; folder.mkdir(exist_ok=True)
        app_icon.save(folder / "AppIcon.png", format="PNG")
        (folder / "Contents.json").write_text(json.dumps({
            "images": [{"filename":"AppIcon.png","idiom":"universal","platform":"ios","size":"1024x1024"}],
            "info":{"author":"xcode","version":1}}, ensure_ascii=False, indent=2) + "\n", encoding="utf8")
        # Catalog is a single byte-identical source resource, not hand-edited iOS product data.
        assert (project / "Shared" / "Resources" / "menu_catalog.json").read_bytes() == z.read("catalog/menus_47.json")
        report = {"source_sha256":SHA256, "menu_images":len(hashes), "menu_hashes":hashes,
                  "brand_logo_source_sha256":hashlib.sha256(raw_logo).hexdigest(),
                  "brand_icon_source_sha256":hashlib.sha256(raw_icon).hexdigest(),
                  "sales_enabled":False}
        (project / "Tools" / "asset_verification.json").write_text(json.dumps(report, ensure_ascii=False, indent=2)+"\n",encoding="utf8")
        return report

if __name__ == "__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--source-zip",type=Path,required=True)
    ap.add_argument("--project",type=Path,required=True)
    args=ap.parse_args()
    print(json.dumps({k:v for k,v in hydrate(args.source_zip,args.project).items() if k!="menu_hashes"},indent=2))
