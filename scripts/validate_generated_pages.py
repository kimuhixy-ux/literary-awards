#!/usr/bin/env python3
"""Validate generated literary award pages and fact-only output rules."""

from __future__ import annotations

import html
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = 795


def fail(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def load_excluded_text() -> set[str]:
    excluded = set()
    def add_long(value: object) -> None:
        if isinstance(value, str) and len(value) >= 20:
            excluded.add(value)

    awards = json.loads((ROOT / "data/awards.json").read_text(encoding="utf-8"))
    for award in awards:
        for key in ("description", "description_en"):
            add_long(award.get(key))
        for relation in award.get("related_awards", []):
            for key in ("note", "note_en"):
                add_long(relation.get(key))
        if not award.get("data_file"):
            continue
        rows = json.loads((ROOT / "data" / award["data_file"]).read_text(encoding="utf-8"))
        for row in rows:
            for key in ("citation_ja", "citation_en", "theme_summary_ja", "theme_summary_en", "notes", "notes_en", "lecture_title"):
                add_long(row.get(key))
            translation = row.get("jp_translation") or {}
            for key in ("note", "note_en"):
                add_long(translation.get(key))
    return excluded


def validate_links(path: Path, text: str) -> None:
    for href in re.findall(r'href="([^"]+)"', text):
        parsed = urlsplit(href.replace("&amp;", "&"))
        if parsed.scheme or parsed.netloc or not parsed.path or parsed.path.startswith("/"):
            continue
        target = (path.parent / unquote(parsed.path)).resolve()
        if target.is_dir():
            target /= "index.html"
        if not target.exists():
            fail(f"{path.relative_to(ROOT)} broken link: {href}")


def main() -> None:
    excluded = load_excluded_text()
    ja = sorted((ROOT / "items").glob("*/index.html"))
    en = sorted((ROOT / "en/items").glob("*/index.html"))
    if len(ja) != EXPECTED or len(en) != EXPECTED:
        fail(f"page count ja={len(ja)} en={len(en)}")
    if [path.parent.name for path in ja] != [path.parent.name for path in en]:
        fail("locale slug sets differ")

    common_required = ['rel="canonical"', 'hreflang="ja"', 'hreflang="en"', 'hreflang="x-default"', '"@type":"WebPage"', '"@type":"BreadcrumbList"', 'name="twitter:card" content="summary_large_image"', 'config.js', 'ads.js']
    total_person = 0
    total_book = 0
    for language, pages in (("ja", ja), ("en", en)):
        titles: set[str] = set()
        descriptions: set[str] = set()
        for path in pages:
            text = path.read_text(encoding="utf-8")
            missing = [value for value in common_required if value not in text]
            if missing:
                fail(f"{path.relative_to(ROOT)} missing {missing}")
            leaked = next((value for value in excluded if value and value in text), None)
            if leaked:
                fail(f"{path.relative_to(ROOT)} reproduces an excluded narrative field")
            title_match = re.search(r"<title>(.*?)</title>", text, re.S)
            meta_match = re.search(r'<meta name="description" content="([^"]*)">', text)
            if not title_match or not meta_match:
                fail(f"{path.relative_to(ROOT)} lacks title or meta description")
            title = html.unescape(title_match.group(1))
            description = html.unescape(meta_match.group(1))
            if title in titles or description in descriptions:
                fail(f"{path.relative_to(ROOT)} has duplicate title or meta description")
            if len(description) > 155:
                fail(f"{path.relative_to(ROOT)} meta description exceeds 155 characters")
            titles.add(title)
            descriptions.add(description)
            match = re.search(r'<script type="application/ld\+json">(.*?)</script>', text, re.S)
            try:
                structured = json.loads(match.group(1) if match else "")
            except json.JSONDecodeError as exc:
                fail(f"{path.relative_to(ROOT)} invalid JSON-LD: {exc}")
            serialized = json.dumps(structured, ensure_ascii=False)
            total_person += '"@type": "Person"' in serialized
            total_book += '"@type": "Book"' in serialized
            validate_links(path, text)

    if total_person != 755 * 2:
        fail(f"expected 1,510 Person entities, found {total_person}")
    if total_book == 0:
        fail("no Book entities generated")

    for path in (ROOT / "items/index.html", ROOT / "en/items/index.html"):
        text = path.read_text(encoding="utf-8")
        if text.count('<li><a href="') != EXPECTED:
            fail(f"{path.relative_to(ROOT)} index count mismatch")
        leaked = next((value for value in excluded if value and value in text), None)
        if leaked:
            fail(f"{path.relative_to(ROOT)} reproduces an excluded narrative field")
        validate_links(path, text)

    root = ET.parse(ROOT / "sitemap.xml").getroot()
    ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    urls = [node.text for node in root.findall("s:url/s:loc", ns)]
    if len(urls) != EXPECTED * 2 + 8 or len(urls) != len(set(urls)):
        fail(f"invalid sitemap URL set: {len(urls)}")
    robots = (ROOT / "robots.txt").read_text(encoding="utf-8")
    if "https://kimuhixy.com/literary-awards/sitemap.xml" not in robots:
        fail("robots.txt sitemap missing")
    print(f"Validated {len(ja) + len(en):,} fact-only detail pages, 2 indexes, and {len(urls):,} sitemap URLs.")


if __name__ == "__main__":
    main()
