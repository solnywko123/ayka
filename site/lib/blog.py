"""Markdown blog posts with a small YAML frontmatter block, e.g.:

---
title: "..."
description: "..."
date: "2026-08-15"
slug: "..."
---

Body in Markdown...
"""
from __future__ import annotations

import re
from pathlib import Path

import markdown as md
import yaml

FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", re.DOTALL)


def parse_markdown_file(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    m = FRONTMATTER_RE.match(text)
    if not m:
        raise ValueError(f"No YAML frontmatter found in {path}")
    meta = yaml.safe_load(m.group(1)) or {}
    body_md = m.group(2).strip()
    meta["html"] = md.markdown(body_md, extensions=["extra", "toc", "sane_lists"])
    meta["word_count"] = len(re.findall(r"\w+", body_md))
    meta.setdefault("slug", path.stem)
    return meta


def load_blog_posts(content_dir: Path, lang: str) -> list[dict]:
    posts_dir = content_dir / lang / "blog"
    posts = []
    if posts_dir.exists():
        for path in sorted(posts_dir.glob("*.md")):
            posts.append(parse_markdown_file(path))
    posts.sort(key=lambda p: p.get("date", ""), reverse=True)
    return posts
