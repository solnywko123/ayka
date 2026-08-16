#!/usr/bin/env python3
"""
Static site generator for Ayka Cleaning (BRIEF.md, разделы 2-3).

Usage:
    python site/build.py                # build once into site/dist
    BUILD_ENV=prod python site/build.py # build in prod mode (fails on placeholder config)
"""
from __future__ import annotations

import datetime as dt
import os
import shutil
import sys
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

SITE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SITE_DIR))

import check_config  # noqa: E402
from lib import assets, blog, content, ogimage, seo  # noqa: E402

TEMPLATES_DIR = SITE_DIR / "templates"
CONTENT_DIR = SITE_DIR / "content"
STATIC_DIR = SITE_DIR / "static"
DIST_DIR = SITE_DIR / "dist"

URL_SLUGS = {
    "uslugi": "uslugi",
    "rayony": "rayony",
    "ceny": "ceny",
    "o-nas": "o-nas",
    "otzyvy": "otzyvy",
    "kontakty": "kontakty",
    "blog": "blog",
}

STATIC_PAGE_KEYS = {"uslugi": "services", "ceny": "ceny", "o-nas": "about", "otzyvy": "otzyvy", "kontakty": "kontakty"}

BUILD_DATE = dt.date.today().isoformat()


def page_path(lang: str, *parts: str) -> str:
    segments = [lang] + [p for p in parts if p]
    return "/" + "/".join(segments) + "/"


def abs_url(domain: str, path: str) -> str:
    return f"https://{domain}{path}"


def write_html(dist_root: Path, path: str, html: str) -> Path:
    out_file = dist_root / path.lstrip("/") / "index.html"
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(html, encoding="utf-8")
    return out_file


class SiteBuilder:
    def __init__(self, build_env: str):
        self.build_env = build_env
        self.config = check_config.run(build_env=build_env)
        self.pricing = content.load_pricing()
        self.languages: list[str] = self.config["languages"]
        self.default_lang: str = self.config["default_language"]
        self.domain: str = self.config["domain"]
        self.demo_banner = bool(self.config.get("_has_placeholders")) and build_env == "dev"

        self.lang_content = {lang: content.load_lang_content(lang) for lang in self.languages}
        self.lang_posts = {lang: blog.load_blog_posts(CONTENT_DIR, lang) for lang in self.languages}

        self.sitemap_pages: list[dict] = []
        self.asset = lambda p: f"/{p}"  # replaced after copying static assets
        self.critical_css = (SITE_DIR / "build_assets" / "critical.css").read_text(encoding="utf-8")

        self.env = Environment(
            loader=FileSystemLoader(str(TEMPLATES_DIR)),
            autoescape=select_autoescape(["html"]),
            trim_blocks=True,
            lstrip_blocks=True,
        )
        self.env.globals["asset"] = lambda p: self.asset(p)

    # ---------- alternates / hreflang ----------

    def alternates_for(self, kind: str, slug: str | None = None) -> dict[str, str]:
        alt: dict[str, str] = {}
        for lang in self.languages:
            if kind == "home":
                alt[lang] = page_path(lang)
            elif kind == "service":
                if content.service_by_slug(self.lang_content[lang]["services"], slug):
                    alt[lang] = page_path(lang, "uslugi", slug)
            elif kind == "district":
                if any(d["slug"] == slug for d in self.lang_content[lang]["districts"]):
                    alt[lang] = page_path(lang, "rayony", slug)
            elif kind == "blog_post":
                if any(p["slug"] == slug for p in self.lang_posts[lang]):
                    alt[lang] = page_path(lang, "blog", slug)
            elif kind == "blog_index":
                alt[lang] = page_path(lang, "blog")
            else:
                alt[lang] = page_path(lang, URL_SLUGS[kind])
        return alt

    # ---------- shared context ----------

    def base_context(self, lang: str, page_type: str, meta: dict, json_ld: list[dict],
                      service_slug: str | None = None) -> dict:
        lang_data = self.lang_content[lang]
        services = lang_data["services"]
        districts = lang_data["districts"]
        ui = lang_data["ui"]

        nav_services = [{"slug": s["slug"], "title": s["title"]} for s in services]
        nav_districts = [{"slug": d["slug"], "title": d["title"]} for d in districts]

        lang_names = {"ru": "Русский", "ky": "Кыргызча", "en": "English"}

        return {
            "lang": lang,
            "langs": self.languages,
            "lang_names": lang_names,
            "default_lang": self.default_lang,
            "config": self.config,
            "pricing": self.pricing,
            "ui": ui,
            "calculator_i18n": lang_data["calculator"],
            "demo_banner": self.demo_banner,
            "meta": meta,
            "json_ld": json_ld,
            "page_type": page_type,
            "service_slug": service_slug or "",
            "nav_services": nav_services,
            "nav_districts": nav_districts,
            "build_date": BUILD_DATE,
            "critical_css": self.critical_css,
        }

    def make_meta(self, lang: str, path: str, title: str, description: str,
                  alternates: dict[str, str], og_title: str, og_subtitle: str) -> dict:
        canonical = abs_url(self.domain, path)
        og_rel = path.lstrip("/") + "og.png"
        og_file = DIST_DIR / og_rel
        ogimage.generate_og_image(og_title, og_subtitle, og_file, brand=self.config["company_name"])
        alt_abs = {l: abs_url(self.domain, u) for l, u in alternates.items()}
        return {
            "title": title,
            "description": description,
            "canonical": canonical,
            "alternates": alt_abs,
            "alt_paths": dict(alternates),
            "og_image": abs_url(self.domain, "/" + og_rel),
        }

    def register_sitemap(self, path: str, alternates: dict[str, str]) -> None:
        alt_abs = {l: abs_url(self.domain, u) for l, u in alternates.items()}
        self.sitemap_pages.append({
            "url": abs_url(self.domain, path),
            "lastmod": BUILD_DATE,
            "alternates": alt_abs,
        })

    def render(self, template_name: str, context: dict) -> str:
        return self.env.get_template(template_name).render(**context)

    # ---------- page builders ----------

    def build_home(self, lang: str) -> None:
        lang_data = self.lang_content[lang]
        pages = lang_data["pages"]["home"]
        alternates = self.alternates_for("home")
        path = page_path(lang)
        meta = self.make_meta(
            lang, path, pages["meta_title"], pages["meta_description"], alternates,
            pages["hero"]["h1"], lang_data["pages"]["home"].get("meta_description", ""),
        )
        reviews = lang_data["reviews"]
        json_ld = [
            seo.local_business_jsonld(self.config, lang, meta["canonical"], reviews=reviews),
            seo.faq_jsonld(lang_data["faq"]),
        ]
        ctx = self.base_context(lang, "home", meta, json_ld)
        ctx.update({
            "home": pages,
            "services": lang_data["services"],
            "faq": lang_data["faq"],
            "reviews": reviews,
            "districts": lang_data["districts"],
        })
        html = self.render("pages/home.html", ctx)
        write_html(DIST_DIR, path, html)
        self.register_sitemap(path, alternates)

    def build_service(self, lang: str, service: dict) -> None:
        lang_data = self.lang_content[lang]
        alternates = self.alternates_for("service", service["slug"])
        path = page_path(lang, "uslugi", service["slug"])
        meta = self.make_meta(
            lang, path, service["meta_title"], service["meta_description"], alternates,
            service["title"], service.get("short_description", ""),
        )
        breadcrumbs = [
            (lang_data["ui"]["nav"]["home"], abs_url(self.domain, page_path(lang))),
            (lang_data["ui"]["nav"]["services"], abs_url(self.domain, page_path(lang, "uslugi"))),
            (service["title"], meta["canonical"]),
        ]
        json_ld = [
            seo.local_business_jsonld(self.config, lang, meta["canonical"]),
            seo.service_jsonld(self.config, service, meta["canonical"]),
            seo.faq_jsonld(service["faq"]),
            seo.breadcrumb_jsonld(breadcrumbs),
        ]
        related = [s for s in lang_data["services"] if s["slug"] in service.get("related", [])]
        ctx = self.base_context(lang, "service", meta, json_ld, service_slug=service["slug"])
        ctx.update({"service": service, "related": related, "breadcrumbs": breadcrumbs})
        html = self.render("pages/service.html", ctx)
        write_html(DIST_DIR, path, html)
        self.register_sitemap(path, alternates)

    def build_district(self, lang: str, district: dict) -> None:
        lang_data = self.lang_content[lang]
        alternates = self.alternates_for("district", district["slug"])
        path = page_path(lang, "rayony", district["slug"])
        meta = self.make_meta(
            lang, path, district["meta_title"], district["meta_description"], alternates,
            district["title"], district.get("intro", ""),
        )
        breadcrumbs = [
            (lang_data["ui"]["nav"]["home"], abs_url(self.domain, page_path(lang))),
            (lang_data["ui"]["geography_title"], abs_url(self.domain, page_path(lang))),
            (district["title"], meta["canonical"]),
        ]
        json_ld = [
            seo.local_business_jsonld(self.config, lang, meta["canonical"]),
            seo.breadcrumb_jsonld(breadcrumbs),
        ]
        ctx = self.base_context(lang, "district", meta, json_ld)
        ctx.update({"district": district, "breadcrumbs": breadcrumbs, "services": lang_data["services"]})
        html = self.render("pages/district.html", ctx)
        write_html(DIST_DIR, path, html)
        self.register_sitemap(path, alternates)

    def build_static_page(self, lang: str, kind: str, template: str) -> None:
        lang_data = self.lang_content[lang]
        page_data = lang_data["pages"][STATIC_PAGE_KEYS[kind]]
        alternates = self.alternates_for(kind)
        path = page_path(lang, URL_SLUGS[kind])
        meta = self.make_meta(
            lang, path, page_data["meta_title"], page_data["meta_description"], alternates,
            page_data.get("h1", page_data["meta_title"]), page_data.get("meta_description", ""),
        )
        breadcrumbs = [
            (lang_data["ui"]["nav"]["home"], abs_url(self.domain, page_path(lang))),
            (page_data.get("h1", ""), meta["canonical"]),
        ]
        json_ld = [
            seo.local_business_jsonld(self.config, lang, meta["canonical"],
                                       reviews=lang_data["reviews"] if kind == "otzyvy" else None),
            seo.breadcrumb_jsonld(breadcrumbs),
        ]
        if kind == "otzyvy":
            json_ld = [
                seo.local_business_jsonld(self.config, lang, meta["canonical"], reviews=lang_data["reviews"]),
                seo.breadcrumb_jsonld(breadcrumbs),
            ]
        ctx = self.base_context(lang, kind, meta, json_ld)
        ctx.update({
            "page": page_data,
            "breadcrumbs": breadcrumbs,
            "services": lang_data["services"],
            "districts": lang_data["districts"],
            "reviews": lang_data["reviews"],
            "screenshots": lang_data["review_screenshots"] if kind == "otzyvy" else None,
        })
        html = self.render(template, ctx)
        write_html(DIST_DIR, path, html)
        self.register_sitemap(path, alternates)

    def build_blog_index(self, lang: str) -> None:
        lang_data = self.lang_content[lang]
        posts = self.lang_posts[lang]
        page_data = lang_data["pages"]["blog"]
        alternates = self.alternates_for("blog_index")
        path = page_path(lang, "blog")
        meta = self.make_meta(
            lang, path, page_data["meta_title"], page_data["meta_description"], alternates,
            page_data.get("h1", page_data["meta_title"]), "",
        )
        breadcrumbs = [
            (lang_data["ui"]["nav"]["home"], abs_url(self.domain, page_path(lang))),
            (page_data.get("h1", ""), meta["canonical"]),
        ]
        json_ld = [seo.local_business_jsonld(self.config, lang, meta["canonical"]), seo.breadcrumb_jsonld(breadcrumbs)]
        ctx = self.base_context(lang, "blog_index", meta, json_ld)
        ctx.update({"posts": posts, "page": page_data, "breadcrumbs": breadcrumbs})
        html = self.render("pages/blog_index.html", ctx)
        write_html(DIST_DIR, path, html)
        self.register_sitemap(path, alternates)

    def build_blog_post(self, lang: str, post: dict) -> None:
        lang_data = self.lang_content[lang]
        alternates = self.alternates_for("blog_post", post["slug"])
        path = page_path(lang, "blog", post["slug"])
        meta = self.make_meta(
            lang, path, post.get("meta_title", post["title"]), post["description"], alternates,
            post["title"], post["description"],
        )
        breadcrumbs = [
            (lang_data["ui"]["nav"]["home"], abs_url(self.domain, page_path(lang))),
            (lang_data["pages"]["blog"].get("h1", ""), abs_url(self.domain, page_path(lang, "blog"))),
            (post["title"], meta["canonical"]),
        ]
        json_ld = [
            seo.local_business_jsonld(self.config, lang, meta["canonical"]),
            seo.article_jsonld(self.config, post, meta["canonical"], meta["og_image"]),
            seo.breadcrumb_jsonld(breadcrumbs),
        ]
        other_posts = [p for p in self.lang_posts[lang] if p["slug"] != post["slug"]][:2]
        ctx = self.base_context(lang, "blog_post", meta, json_ld)
        ctx.update({"post": post, "breadcrumbs": breadcrumbs, "other_posts": other_posts,
                    "services": lang_data["services"]})
        html = self.render("pages/blog_post.html", ctx)
        write_html(DIST_DIR, path, html)
        self.register_sitemap(path, alternates)

    def build_404(self, lang: str) -> None:
        lang_data = self.lang_content[lang]
        page_data = lang_data["pages"]["not_found"]
        path = page_path(lang, "404")
        meta = {
            "title": page_data["meta_title"],
            "description": page_data["meta_description"],
            "canonical": abs_url(self.domain, page_path(lang)),
            "alternates": {},
            "alt_paths": {l: page_path(l) for l in self.languages},
            "og_image": abs_url(self.domain, "/img/og-default.png"),
        }
        ctx = self.base_context(lang, "404", meta, [])
        ctx.update({"page": page_data, "services": lang_data["services"]})
        html = self.render("pages/404.html", ctx)
        out_file = DIST_DIR / lang / "404.html"
        out_file.parent.mkdir(parents=True, exist_ok=True)
        out_file.write_text(html, encoding="utf-8")
        if lang == self.default_lang:
            root_404 = DIST_DIR / "404.html"
            root_404.write_text(html, encoding="utf-8")

    def build_root_redirect(self) -> None:
        target = page_path(self.default_lang)
        html = (
            "<!doctype html><html lang=\"" + self.default_lang + "\"><head>"
            "<meta charset=\"utf-8\">"
            f"<meta http-equiv=\"refresh\" content=\"0; url={target}\">"
            f"<link rel=\"canonical\" href=\"{abs_url(self.domain, target)}\">"
            "<title>Ayka Cleaning</title>"
            "</head><body>"
            f"<p>Переход на <a href=\"{target}\">{target}</a>...</p>"
            "</body></html>"
        )
        (DIST_DIR / "index.html").write_text(html, encoding="utf-8")

    def build_default_og_image(self) -> None:
        ogimage.generate_og_image(
            self.config["company_name"],
            self.config["tagline"][self.default_lang],
            DIST_DIR / "img" / "og-default.png",
            brand=self.config["company_name"],
        )

    def write_sitemap_and_robots(self) -> None:
        sitemap_xml = seo.generate_sitemap(self.sitemap_pages)
        (DIST_DIR / "sitemap.xml").write_text(sitemap_xml, encoding="utf-8")
        (DIST_DIR / "robots.txt").write_text(seo.generate_robots(self.domain), encoding="utf-8")

    def run(self) -> None:
        if DIST_DIR.exists():
            shutil.rmtree(DIST_DIR)
        DIST_DIR.mkdir(parents=True)

        manifest = assets.copy_static_tree(STATIC_DIR, DIST_DIR)
        self.asset = assets.make_asset_fn(manifest)

        self.build_default_og_image()

        for lang in self.languages:
            self.build_home(lang)
            for service in self.lang_content[lang]["services"]:
                self.build_service(lang, service)
            for district in self.lang_content[lang]["districts"]:
                self.build_district(lang, district)
            self.build_static_page(lang, "uslugi", "pages/services_index.html")
            self.build_static_page(lang, "ceny", "pages/prices.html")
            self.build_static_page(lang, "o-nas", "pages/about.html")
            self.build_static_page(lang, "otzyvy", "pages/reviews.html")
            self.build_static_page(lang, "kontakty", "pages/contacts.html")
            self.build_blog_index(lang)
            for post in self.lang_posts[lang]:
                self.build_blog_post(lang, post)
            self.build_404(lang)

        self.build_root_redirect()
        self.write_sitemap_and_robots()

        page_count = len(self.sitemap_pages)
        print(f"build.py: собрано {page_count} страниц x {len(self.languages)} языков в {DIST_DIR}")


def main() -> None:
    build_env = os.environ.get("BUILD_ENV", "dev")
    builder = SiteBuilder(build_env)
    builder.run()


if __name__ == "__main__":
    main()
