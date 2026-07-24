#!/usr/bin/env python3
"""Wikidataから登録作家の著作を補完し、邦訳状態を安全側に正規化する。

Wikidataで著者(P50)が明示された作品だけを採用する。日本語原著は
``original-ja``、NDL等の個別書誌で確認済みのものは ``available``、
それ以外は未邦訳と断定せず ``unverified`` とする。
"""
import argparse
import json
import re
import time
import unicodedata
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
TRANSLATIONS = DATA / "author_work_translations.json"
EXCLUSIONS = DATA / "work_exclusions.json"
EQUIVALENCES = DATA / "work_equivalences.json"
ENDPOINT = "https://query.wikidata.org/sparql"
SOURCE = "https://www.wikidata.org/wiki/"


def norm(value):
    value = unicodedata.normalize("NFKC", value or "").casefold()
    return re.sub(r"[^0-9a-z\u00c0-\u024f\u3040-\u30ff\u3400-\u9fff]", "", value)


def sparql(query):
    url = ENDPOINT + "?" + urllib.parse.urlencode({"query": query, "format": "json"})
    req = urllib.request.Request(url, headers={"User-Agent": "literary-awards/2.0 (bibliography enrichment)"})
    with urllib.request.urlopen(req, timeout=90) as response:
        return json.load(response)["results"]["bindings"]


def esc(value):
    return value.replace("\\", "\\\\").replace('"', '\\"')


def chunks(values, size):
    for start in range(0, len(values), size):
        yield values[start:start + size]


def fetch(authors):
    found = {}
    for number, batch in enumerate(chunks(authors, 35), 1):
        labels = []
        for author in batch:
            if author.get("name_en"):
                labels.append(f'"{esc(author["name_en"])}"@en')
            if author.get("name_ja"):
                labels.append(f'"{esc(author["name_ja"])}"@ja')
        query = """
SELECT DISTINCT ?wanted ?author ?work ?titleEn ?titleJa ?date WHERE {
  VALUES ?wanted { %s }
  ?author rdfs:label ?wanted .
  ?work wdt:P50 ?author .
  OPTIONAL { ?work rdfs:label ?titleEn FILTER(LANG(?titleEn) = "en") }
  OPTIONAL { ?work rdfs:label ?titleJa FILTER(LANG(?titleJa) = "ja") }
  OPTIONAL { ?work wdt:P577 ?date }
}
""" % " ".join(labels)
        for row in sparql(query):
            wanted = row.get("wanted", {}).get("value")
            matches = [a for a in batch if wanted in (a.get("name_en"), a.get("name_ja"))]
            if len(matches) != 1:
                continue
            aid = matches[0]["author_id"]
            title = row.get("titleEn", {}).get("value") or row.get("titleJa", {}).get("value")
            if not title:
                continue
            qid = row["work"]["value"].rsplit("/", 1)[-1]
            date = row.get("date", {}).get("value", "")
            found.setdefault(aid, {})[qid] = {
                "title_original": title,
                "title_ja": row.get("titleJa", {}).get("value"),
                "year": int(date[:4]) if re.match(r"^\d{4}", date) else None,
                "theme_summary_ja": None,
                "source_urls": [SOURCE + qid],
            }
        print(f"Wikidata {number}: {len(found)} authors matched")
        time.sleep(0.4)
    return found


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--fetch", action="store_true")
    args = parser.parse_args()
    authors = json.loads((DATA / "authors.json").read_text())
    path = DATA / "major_works.json"
    works = json.loads(path.read_text())
    overrides = json.loads(TRANSLATIONS.read_text()) if TRANSLATIONS.exists() else {}
    exclusions = json.loads(EXCLUSIONS.read_text()) if EXCLUSIONS.exists() else {}
    equivalences = json.loads(EQUIVALENCES.read_text()) if EQUIVALENCES.exists() else {}
    award_titles = {
        a["author_id"]: {
            norm(title)
            for w in a.get("representative_works", [])
            for title in (w.get("work_original"), w.get("work_ja"))
            if title
        }
        for a in authors
    }
    fetched = fetch(authors) if args.fetch else {}
    for author in authors:
        aid = author["author_id"]
        current = [w for w in works.setdefault(aid, [])
                   if norm(w.get("title_original")) not in award_titles[aid]
                   and (not w.get("title_ja") or norm(w.get("title_ja")) not in award_titles[aid])
                   and not any(url.rsplit("/", 1)[-1] in exclusions.get(aid, []) for url in w.get("source_urls", []))]
        works[aid] = current
        seen = {norm(w.get("title_original")) for w in current} | {norm(w.get("title_ja")) for w in current}
        for work in fetched.get(aid, {}).values():
            if any(url.rsplit("/", 1)[-1] in exclusions.get(aid, []) for url in work.get("source_urls", [])):
                continue
            if norm(work["title_original"]) in seen or norm(work["title_original"]) in award_titles[aid]:
                continue
            current.append(work)
            seen.add(norm(work["title_original"]))
        for work in current:
            work.setdefault("source_urls", [])
            translation = work.setdefault("jp_translation", {})
            if author.get("country") == "日本":
                translation["status"] = "original-ja"
                translation.setdefault("note", "日本語原著")
            elif translation.get("status") != "available":
                translation["status"] = "unverified"
                translation.setdefault("note", "邦訳書誌を個別確認できていません")
            override = overrides.get(f"{aid}:{work.get('title_original')}")
            if override:
                source = override.get("source_url")
                work["title_ja"] = override.get("title_ja") or work.get("title_ja")
                work["jp_translation"] = {k: v for k, v in override.items() if k != "source_url"}
                if source and source not in work["source_urls"]:
                    work["source_urls"].append(source)
        by_title = {work.get("title_original"): work for work in current}
        remove = set()
        for canonical_title, alternate_titles in equivalences.get(aid, {}).items():
            canonical = by_title.get(canonical_title)
            if not canonical:
                continue
            members = [by_title[title] for title in alternate_titles if title in by_title]
            for member in members:
                canonical["source_urls"] = list(dict.fromkeys([
                    *canonical.get("source_urls", []), *member.get("source_urls", [])
                ]))
                if not canonical.get("theme_summary_ja") and member.get("theme_summary_ja"):
                    canonical["theme_summary_ja"] = member["theme_summary_ja"]
                if canonical.get("jp_translation", {}).get("status") != "available" \
                        and member.get("jp_translation", {}).get("status") == "available":
                    canonical["jp_translation"] = member["jp_translation"]
                    canonical["title_ja"] = member.get("title_ja") or canonical.get("title_ja")
                remove.add(member["title_original"])
        if remove:
            current[:] = [work for work in current if work.get("title_original") not in remove]
        current.sort(key=lambda w: (w.get("year") is None, w.get("year") or 0, w.get("title_original") or ""))
    path.write_text(json.dumps(works, ensure_ascii=False, indent=2) + "\n")
    print(f"{len(works)} authors / {sum(map(len, works.values()))} non-award works")


if __name__ == "__main__":
    main()
