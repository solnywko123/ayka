"""Static asset pipeline: content-hashed filenames for CSS/JS (long-cache friendly),
plain copy for fonts/icons/img (see DECISIONS.md for why those aren't hashed)."""
from __future__ import annotations

import hashlib
import shutil
from pathlib import Path

HASHED_EXTENSIONS = {".css", ".js"}
PLAIN_SUBDIRS = ["fonts", "icons", "img"]
HASHED_SUBDIRS = ["css", "js"]


def _hash_file(path: Path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest()[:10]


def copy_static_tree(static_root: Path, dist_root: Path) -> dict[str, str]:
    manifest: dict[str, str] = {}

    for sub in HASHED_SUBDIRS:
        src_dir = static_root / sub
        if not src_dir.exists():
            continue
        dst_dir = dist_root / sub
        dst_dir.mkdir(parents=True, exist_ok=True)
        for f in sorted(src_dir.glob("*")):
            if not f.is_file():
                continue
            if f.suffix in HASHED_EXTENSIONS:
                digest = _hash_file(f)
                new_name = f"{f.stem}.{digest}{f.suffix}"
            else:
                new_name = f.name
            shutil.copy2(f, dst_dir / new_name)
            manifest[f"{sub}/{f.name}"] = f"/{sub}/{new_name}"

    for sub in PLAIN_SUBDIRS:
        src_dir = static_root / sub
        if not src_dir.exists():
            continue
        dst_dir = dist_root / sub
        shutil.copytree(src_dir, dst_dir, dirs_exist_ok=True)

    return manifest


def make_asset_fn(manifest: dict[str, str]):
    def asset(rel_path: str) -> str:
        return manifest.get(rel_path, f"/{rel_path}")

    return asset
