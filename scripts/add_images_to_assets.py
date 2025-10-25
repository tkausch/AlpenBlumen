#!/usr/bin/env python3
"""
add_images_to_assets.py
-----------------------
Copy all JPG files from scripts/images into the Xcode asset catalog, creating one
imageset per file (single-scale universal entry).

Usage:
    python add_images_to_assets.py
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
IMAGES_DIR = SCRIPT_DIR / "images"
ASSETS_DIR = SCRIPT_DIR.parent / "AlpenBlumen" / "assets" / "Assets.xcassets"


def ensure_paths() -> None:
    if not IMAGES_DIR.exists():
        raise SystemExit(f"Images directory not found: {IMAGES_DIR}")
    if not ASSETS_DIR.exists():
        raise SystemExit(f"Asset catalog not found: {ASSETS_DIR}")


def write_contents_json(imageset_dir: Path, filename: str) -> None:
    contents = {
        "images": [
            {
                "filename": filename,
                "idiom": "universal",
                "scale": "1x",
            }
        ],
        "info": {
            "author": "xcode",
            "version": 1,
        },
    }
    with (imageset_dir / "Contents.json").open("w", encoding="utf-8") as fh:
        json.dump(contents, fh, indent=2)
        fh.write("\n")


def import_images() -> int:
    ensure_paths()
    count = 0
    image_files = sorted(
        p for p in IMAGES_DIR.glob("*") if p.is_file() and p.suffix.lower() in {".jpg", ".jpeg"}
    )
    for image_path in image_files:
        stem = image_path.stem
        imageset_dir = ASSETS_DIR / f"{stem}.imageset"
        imageset_dir.mkdir(parents=True, exist_ok=True)
        for existing in imageset_dir.iterdir():
            if existing.is_file() and existing.name != "Contents.json":
                existing.unlink()
        target_image = imageset_dir / image_path.name
        shutil.copy2(image_path, target_image)
        write_contents_json(imageset_dir, image_path.name)
        count += 1
    return count


def main() -> None:
    imported = import_images()
    print(f"Imported {imported} image(s) into {ASSETS_DIR}")


if __name__ == "__main__":
    main()
