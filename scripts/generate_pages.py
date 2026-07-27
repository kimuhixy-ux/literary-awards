#!/usr/bin/env python3
"""Generate bilingual, fact-only literary award record pages."""

from __future__ import annotations

import html
import json
import re
import shutil
import unicodedata
from collections import defaultdict
from pathlib import Path
from string import Template

ROOT = Path(__file__).resolve().parents[1]
BASE = "https://kimuhixy.com/literary-awards"
OG_IMAGE = f"{BASE}/icons/icon-512.png"


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def load_data() -> tuple[list[dict], dict[str, dict]]:
    awards = json.loads((ROOT / "data/awards.json").read_text(encoding="utf-8"))
    award_map = {award["id"]: award for award in awards if award.get("data_file")}
    records = []
    for award_id, award in award_map.items():
        rows = json.loads((ROOT / "data" / award["data_file"]).read_text(encoding="utf-8"))
        for position, row in enumerate(rows, 1):
            if "year" not in row or "source_urls" not in row:
                raise ValueError(f"{award_id} record {position} lacks year or source_urls")
            records.append({**row, "award_id": award_id, "_position": position})
    return records, award_map


def ascii_slug(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", normalized).strip("-")


def make_slugs(records: list[dict]) -> list[str]:
    used: set[str] = set()
    slugs = []
    for row in records:
        identity = row.get("author_id") or ascii_slug(row.get("author_en") or "") or ("no-award" if not row.get("author_ja") else f'recipient-{row["_position"]}')
        round_part = f'-{row["round"]}' if row.get("round") is not None else ""
        base = ascii_slug(f'{row["award_id"]}-{row["year"]}{round_part}-{identity}') or f'record-{row["_position"]}'
        slug = base
        suffix = 2
        while slug in used or slug == "index":
            slug = f"{base}-{suffix}"
            suffix += 1
        used.add(slug)
        slugs.append(slug)
    return slugs


def label(row: dict, key_ja: str, key_en: str, english: bool) -> str:
    if english:
        return row.get(key_en) or row.get(key_ja) or ""
    return row.get(key_ja) or row.get(key_en) or ""


def author_name(row: dict, english: bool) -> str:
    return label(row, "author_ja", "author_en", english)


def work_name(row: dict, english: bool) -> str:
    if english:
        return row.get("work_en") or row.get("work_original") or row.get("work_ja") or ""
    return row.get("work_ja") or row.get("work_original") or row.get("work_en") or ""


def session_name(row: dict, english: bool) -> str:
    if row.get("round") is not None:
        return f'No. {row["round"]}' if english else f'第{row["round"]}回'
    if row.get("session"):
        return str(row["session"])
    return ""


def page_subject(row: dict, award: dict, english: bool) -> str:
    author = author_name(row, english)
    award_name = label(award, "name_ja", "name_en", english)
    session = session_name(row, english)
    edition = f" {session}" if session else ""
    if author:
        return f"{author} — {award_name} {row['year']}{edition}" if english else f"{author} — {award_name}（{row['year']}年{edition}）"
    return f"No award — {award_name} {row['year']}{edition}" if english else f"該当作なし — {award_name}（{row['year']}年{edition}）"


def meta_description(row: dict, award: dict, english: bool) -> str:
    award_name = label(award, "name_ja", "name_en", english)
    author = author_name(row, english)
    work = work_name(row, english)
    session = session_name(row, english)
    edition = f" {session}" if session else ""
    if english:
        if author:
            text = f"{author}, {award_name} recipient for {row['year']}{edition}."
            if work:
                text += f" Winning work: {work}."
            text += " View country, language, translation details, and sources."
        else:
            text = f"No qualifying recipient or work was selected for the {row['year']}{edition} {award_name}. View record details and sources."
    else:
        if author:
            text = f"{row['year']}年{edition}{award_name}の受賞者は{author}です。"
            if work:
                text += f"受賞作は『{work}』。"
            text += "国・言語・邦訳情報・出典を確認できます。"
        else:
            text = f"{row['year']}年{edition}{award_name}は該当作なし。回次、記録情報、出典を確認できます。"
    return text if len(text) <= 155 else text[:154].rstrip() + "…"


def fact(label_text: str, value: object) -> str:
    return f"<div><dt>{esc(label_text)}</dt><dd>{esc(value)}</dd></div>"


def translation_facts(row: dict, english: bool) -> str:
    translation = row.get("jp_translation") or {}
    status = translation.get("status")
    if status == "available":
        pieces = [translation.get("title_ja"), translation.get("translator"), translation.get("publisher"), translation.get("year")]
        value = " / ".join(str(piece) for piece in pieces if piece)
    elif status == "original-ja":
        value = "Japanese original" if english else "日本語原作"
    elif status == "unavailable":
        value = "No confirmed Japanese translation" if english else "確認できた邦訳なし"
    else:
        return ""
    return fact("Japanese edition" if english else "邦訳情報", value)


def related_indices(records: list[dict]) -> list[list[int]]:
    result = []
    for i, row in enumerate(records):
        ranked = sorted(
            (j for j in range(len(records)) if j != i),
            key=lambda j: (
                -(bool(row.get("author_id")) and records[j].get("author_id") == row.get("author_id")),
                -(records[j]["award_id"] == row["award_id"]),
                -(records[j]["year"] == row["year"]),
                abs(records[j]["year"] - row["year"]),
                records[j]["award_id"],
                records[j]["_position"],
            ),
        )
        result.append(ranked[:6])
    return result


def schema(row: dict, award: dict, slug: str, english: bool) -> str:
    lang = "en" if english else "ja"
    prefix = "en/" if english else ""
    canonical = f"{BASE}/{prefix}items/{slug}/"
    subject = page_subject(row, award, english)
    graph: list[dict] = [
        {"@type": "WebSite", "@id": f"{BASE}/#website", "url": f"{BASE}/", "name": "World Literary Prizes Overview" if english else "世界文学賞総覧", "inLanguage": ["ja", "en"]},
        {"@type": "WebPage", "@id": f"{canonical}#webpage", "url": canonical, "name": subject, "inLanguage": lang, "isPartOf": {"@id": f"{BASE}/#website"}},
    ]
    person_id = f"{canonical}#person"
    author = author_name(row, english)
    if author:
        person = {"@type": "Person", "@id": person_id, "name": author, "award": f'{label(award, "name_ja", "name_en", english)} ({row["year"]})'}
        alternate = label(row, "author_en", "author_ja", english)
        if alternate and alternate != author:
            person["alternateName"] = alternate
        graph.append(person)
        graph[1]["mainEntity"] = {"@id": person_id}
    work = work_name(row, english)
    if work:
        book = {"@type": "Book", "@id": f"{canonical}#book", "name": work}
        if author:
            book["author"] = {"@id": person_id}
        original = row.get("work_original")
        if original and original != work:
            book["alternateName"] = original
        language = label(row, "language", "language_en", english)
        if language:
            book["inLanguage"] = language
        graph.append(book)
    graph.append({"@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": 1, "name": "Home" if english else "トップ", "item": f"{BASE}/{prefix}"},
        {"@type": "ListItem", "position": 2, "name": "Award record index" if english else "文学賞受賞記録索引", "item": f"{BASE}/{prefix}items/"},
        {"@type": "ListItem", "position": 3, "name": subject, "item": canonical},
    ]})
    return json.dumps({"@context": "https://schema.org", "@graph": graph}, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")


def detail_context(row: dict, award: dict, slug: str, related: list[int], records: list[dict], awards: dict[str, dict], slugs: list[str], english: bool) -> dict[str, str]:
    award_name = label(award, "name_ja", "name_en", english)
    author = author_name(row, english)
    work = work_name(row, english)
    subject = page_subject(row, award, english)
    labels = ("Award", "Year", "Session", "Recipient", "Country or region", "Language", "Winning work", "Original title", "Translator") if english else ("文学賞", "受賞年", "回次", "受賞者", "国・地域", "言語", "受賞作", "原題", "英訳者")
    facts = fact(labels[0], award_name) + fact(labels[1], row["year"])
    values = [session_name(row, english), author or ("No qualifying recipient" if english else "該当者なし"), label(row, "country", "country_en", english), label(row, "language", "language_en", english), work, row.get("work_original") if row.get("work_original") != work else "", row.get("translator_en")]
    for label_text, value in zip(labels[2:], values):
        if value:
            facts += fact(label_text, value)
    facts += translation_facts(row, english)
    related_links = []
    for i in related:
        related_award = awards[records[i]["award_id"]]
        related_links.append(f'<li><a href="../{slugs[i]}/">{esc(page_subject(records[i], related_award, english))}</a></li>')
    sources = "".join(f'<li><a href="{esc(url)}" target="_blank" rel="noopener noreferrer">{esc(url)}</a></li>' for url in row["source_urls"])
    prefix = "en/" if english else ""
    app_root = "../../../" if english else "../../"
    app_url = f'{app_root}{"en/" if english else ""}#/award/{row["award_id"]}'
    return {
        "slug": slug, "title": esc(subject), "page_title": esc(f"{subject} | {'Literary Award Record' if english else '文学賞受賞記録'}"),
        "meta_description": esc(meta_description(row, award, english)), "canonical": f"{BASE}/{prefix}items/{slug}/",
        "ja_url": f"{BASE}/items/{slug}/", "en_url": f"{BASE}/en/items/{slug}/", "og_image": OG_IMAGE,
        "json_ld": schema(row, award, slug, english), "award_name": esc(award_name), "facts": facts,
        "app_url": app_url, "official_url": esc(award["official_url"]), "sources": sources,
        "related": "".join(related_links),
    }


def index_groups(records: list[dict], awards: dict[str, dict], slugs: list[str], english: bool) -> str:
    grouped: dict[str, list[tuple[int, str, str]]] = defaultdict(list)
    for row, slug in zip(records, slugs):
        award_name = label(awards[row["award_id"]], "name_ja", "name_en", english)
        grouped[award_name].append((row["year"], slug, page_subject(row, awards[row["award_id"]], english)))
    sections = []
    for award_name in sorted(grouped):
        links = "".join(f'<li><a href="{slug}/">{esc(subject)}</a><span>{year}</span></li>' for year, slug, subject in sorted(grouped[award_name], key=lambda x: (x[0], x[1]), reverse=True))
        sections.append(f'<section class="award-index-group"><h2>{esc(award_name)}</h2><ul>{links}</ul></section>')
    return "".join(sections)


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.rstrip() + "\n", encoding="utf-8")


def main() -> None:
    records, awards = load_data()
    slugs = make_slugs(records)
    related = related_indices(records)
    templates = {name: Template((ROOT / f"templates/{name}.html").read_text(encoding="utf-8")) for name in ("detail_ja", "detail_en", "index_ja", "index_en")}
    for directory in (ROOT / "items", ROOT / "en/items"):
        if directory.exists():
            shutil.rmtree(directory)
    for i, (row, slug) in enumerate(zip(records, slugs)):
        award = awards[row["award_id"]]
        write(ROOT / "items" / slug / "index.html", templates["detail_ja"].substitute(detail_context(row, award, slug, related[i], records, awards, slugs, False)))
        write(ROOT / "en/items" / slug / "index.html", templates["detail_en"].substitute(detail_context(row, award, slug, related[i], records, awards, slugs, True)))
    common = {"count": f"{len(records):,}", "ja_url": f"{BASE}/items/", "en_url": f"{BASE}/en/items/"}
    write(ROOT / "items/index.html", templates["index_ja"].substitute(common, groups=index_groups(records, awards, slugs, False)))
    write(ROOT / "en/items/index.html", templates["index_en"].substitute(common, groups=index_groups(records, awards, slugs, True)))
    urls = [f"{BASE}/", f"{BASE}/en/", f"{BASE}/about.html", f"{BASE}/en/about.html", f"{BASE}/privacy.html", f"{BASE}/en/privacy.html", f"{BASE}/items/", f"{BASE}/en/items/"]
    urls += [f"{BASE}/items/{slug}/" for slug in slugs] + [f"{BASE}/en/items/{slug}/" for slug in slugs]
    sitemap = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + "".join(f"  <url><loc>{esc(url)}</loc></url>\n" for url in urls) + "</urlset>\n"
    write(ROOT / "sitemap.xml", sitemap)
    write(ROOT / "robots.txt", f"User-agent: *\nAllow: /\n\nSitemap: {BASE}/sitemap.xml\n")
    print(f"Generated {len(records) * 2:,} detail pages, 2 indexes, and {len(urls):,} sitemap URLs.")


if __name__ == "__main__":
    main()
