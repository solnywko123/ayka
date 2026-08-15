"""BRIEF.md раздел 15: сборка проходит без ошибок, у всех страниц есть
title/description/canonical/h1, в sitemap нет битых путей, валидность JSON-LD."""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse

import pytest

SITE_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = SITE_DIR.parent
DIST_DIR = SITE_DIR / "dist"
CONTENT_DIR = SITE_DIR / "content"

LINK_RE = re.compile(r'(?:href|src)="(/[^"#]*)"')


@pytest.fixture(scope="module", autouse=True)
def built_site():
    env = dict(os.environ)
    env["BUILD_ENV"] = "dev"
    env["PYTHONIOENCODING"] = "utf-8"
    result = subprocess.run(
        [sys.executable, str(SITE_DIR / "build.py")],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
    )
    assert result.returncode == 0, f"build.py failed:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    yield


def _content_pages() -> list[Path]:
    """Все сгенерированные HTML-страницы, кроме технического редиректа в корне."""
    pages = [f for f in DIST_DIR.rglob("index.html") if f != DIST_DIR / "index.html"]
    pages += list(DIST_DIR.glob("*/404.html"))
    return pages


def test_build_produces_core_files():
    assert (DIST_DIR / "sitemap.xml").exists()
    assert (DIST_DIR / "robots.txt").exists()
    assert (DIST_DIR / "index.html").exists()
    assert (DIST_DIR / "img" / "og-default.png").exists()


def test_every_page_has_title_description_canonical_and_one_h1():
    pages = _content_pages()
    assert len(pages) >= 60  # 3 языка x (home + 6 услуг + 7 районов + uslugi + 4 статичных + blog + 3 поста)
    for page in pages:
        text = page.read_text(encoding="utf-8")
        rel = page.relative_to(DIST_DIR)
        assert re.search(r"<title>[^<]+</title>", text), f"{rel}: missing <title>"
        assert re.search(r'<meta name="description" content="[^"]+"', text), f"{rel}: missing meta description"
        assert 'rel="canonical"' in text, f"{rel}: missing canonical link"
        h1_count = len(re.findall(r"<h1[ >]", text))
        assert h1_count == 1, f"{rel}: expected exactly one <h1>, found {h1_count}"


def test_json_ld_is_valid_json_everywhere():
    checked_any = False
    for page in _content_pages():
        text = page.read_text(encoding="utf-8")
        for block in re.findall(r'<script type="application/ld\+json">(.*?)</script>', text, re.S):
            checked_any = True
            try:
                json.loads(block)
            except json.JSONDecodeError as exc:
                pytest.fail(f"{page.relative_to(DIST_DIR)}: invalid JSON-LD ({exc})")
    assert checked_any


def test_no_aggregate_rating_while_reviews_are_placeholders():
    """BRIEF.md раздел 5.1 п.6 / 17: AggregateRating запрещён, пока в reviews.json есть placeholder."""
    for lang in ["ru", "ky", "en"]:
        reviews = json.loads((CONTENT_DIR / lang / "reviews.json").read_text(encoding="utf-8"))
        assert any(r.get("placeholder") for r in reviews["items"]), (
            f"{lang}/reviews.json: тест ожидает демо-данные с placeholder=true; "
            "если это уже реальные отзывы — обновите тест вместе с данными"
        )
    for page in _content_pages():
        text = page.read_text(encoding="utf-8")
        assert "AggregateRating" not in text, f"{page.relative_to(DIST_DIR)}: AggregateRating недопустим с demo-отзывами"


def test_sitemap_has_no_broken_paths():
    sitemap = (DIST_DIR / "sitemap.xml").read_text(encoding="utf-8")
    locs = re.findall(r"<loc>(https://[^<]+)</loc>", sitemap)
    assert len(locs) >= 60
    for loc in locs:
        rel_path = urlparse(loc).path.lstrip("/")
        target = DIST_DIR / rel_path / "index.html"
        assert target.exists(), f"sitemap references a page that wasn't built: {loc}"


def test_no_broken_internal_links():
    broken = []
    for f in DIST_DIR.rglob("*.html"):
        text = f.read_text(encoding="utf-8")
        for link in LINK_RE.findall(text):
            if link.startswith("//"):
                continue
            target = DIST_DIR / link.lstrip("/") / "index.html" if link.endswith("/") else DIST_DIR / link.lstrip("/")
            if not target.exists():
                broken.append(f"{f.relative_to(DIST_DIR)} -> {link}")
    assert not broken, f"Broken internal links:\n" + "\n".join(broken[:30])


def test_hreflang_alternates_are_reciprocal():
    """Если /ru/uslugi/x/ ссылается на hreflang=ky, соответствующая ky-страница тоже должна существовать."""
    for f in DIST_DIR.rglob("index.html"):
        if f == DIST_DIR / "index.html":
            continue
        text = f.read_text(encoding="utf-8")
        alt_paths = re.findall(r'rel="alternate" hreflang="[a-z]+" href="(https://[^"]+)"', text)
        for alt_url in alt_paths:
            rel_path = urlparse(alt_url).path.lstrip("/")
            target = DIST_DIR / rel_path / "index.html"
            assert target.exists(), f"{f.relative_to(DIST_DIR)}: hreflang points to missing page {alt_url}"


@pytest.mark.parametrize("lang", ["ru", "ky", "en"])
def test_district_pages_have_min_350_unique_words(lang):
    districts = json.loads((CONTENT_DIR / lang / "districts.json").read_text(encoding="utf-8"))["items"]
    assert len(districts) == 7
    for district in districts:
        text = district["intro"] + " " + " ".join(district["body"])
        word_count = len(text.split())
        assert word_count >= 350, f"{lang}/{district['slug']}: only {word_count} words (need >= 350)"


def test_blog_posts_have_min_1200_words():
    for lang in ["ru", "ky", "en"]:
        posts_dir = CONTENT_DIR / lang / "blog"
        posts = list(posts_dir.glob("*.md"))
        assert len(posts) == 3
        for post in posts:
            body = post.read_text(encoding="utf-8").split("---", 2)[-1]
            word_count = len(body.split())
            assert word_count >= 1200, f"{lang}/{post.name}: only {word_count} words (need >= 1200)"
