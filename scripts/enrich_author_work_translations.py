#!/usr/bin/env python3
"""全登録作家の受賞作以外について、NDL Searchで邦訳書誌を一括照合する。"""
import argparse
import json
import re
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from enrich_phase2_translations import SRU, norm, parse_records

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
AUTHORS = DATA / "authors.json"
WORKS = DATA / "major_works.json"
OVERRIDES = DATA / "author_work_translations.json"


def fetch_page(author, start):
    query = f'creator="{author}"'
    url = SRU + "?" + urllib.parse.urlencode({
        "operation": "searchRetrieve", "version": "1.2", "recordSchema": "dcndl",
        "maximumRecords": 200, "startRecord": start, "query": query,
    })
    req = urllib.request.Request(url, headers={"User-Agent": "literary-awards-bibliography/2.0"})
    with urllib.request.urlopen(req, timeout=60) as response:
        return list(parse_records(response.read()))


def bibliography(author):
    # 1作家あたり上位200件。採用時は原題・著者・訳者をさらに完全照合する。
    return fetch_page(author, 1)


def translators(creators):
    values = []
    for creator in creators:
        for match in re.finditer(r"([^;；,，]+?)\s*訳(?:$|[\s,，])", creator):
            value = match.group(1).strip().strip("/／")
            if value and value not in values:
                values.append(value)
    return "・".join(values) or None


def clean_publisher(value):
    value = value or ""
    value = re.split(r"\s+(?=[ァ-ヶー]{3,}(?:\s|$))", value)[0]
    return re.sub(r"\s+(東京|京都|大阪|北京)$", "", value).strip() or None


def check_author(author, works):
    name = author.get("name_en") or author.get("name_ja")
    if not name:
        return {}
    surname = name.split()[-1]
    records = bibliography(name)
    by_original = {}
    for item in records:
        if not any(norm(surname) in norm(c) for c in item["creators"]):
            continue
        translator = translators(item["creators"])
        if not item.get("title") or not item.get("publisher") or not translator:
            continue
        for original in item["originals"]:
            by_original.setdefault(norm(original), []).append((item, translator))
    found = {}
    for work in works:
        if (work.get("jp_translation") or {}).get("status") != "unverified":
            continue
        hits = by_original.get(norm(work.get("title_original")), [])
        if not hits:
            continue
        hits.sort(key=lambda pair: (pair[0].get("year") or 9999, len(pair[0].get("title") or "")))
        item, translator = hits[0]
        found[f'{author["author_id"]}:{work["title_original"]}'] = {
            "status": "available", "title_ja": item["title"], "translator": translator,
            "publisher": clean_publisher(item["publisher"]), "year": item.get("year"),
            "note": "国立国会図書館サーチで書誌確認", "source_url": item.get("url"),
        }
    return found


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--author-id", action="append", default=[])
    args = parser.parse_args()
    authors = json.loads(AUTHORS.read_text())
    works = json.loads(WORKS.read_text())
    saved = json.loads(OVERRIDES.read_text()) if OVERRIDES.exists() else {}
    pending = [a for a in authors if any(
        (w.get("jp_translation") or {}).get("status") == "unverified"
        for w in works.get(a["author_id"], [])
    )]
    if args.author_id:
        wanted = set(args.author_id)
        pending = [a for a in pending if a["author_id"] in wanted]
    if args.limit:
        pending = pending[:args.limit]
    checked = matched = 0
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(check_author, author, works[author["author_id"]]): author for author in pending}
        for future in as_completed(futures):
            author = futures[future]
            try:
                found = future.result()
            except Exception as exc:
                print(f'ERROR {author["author_id"]}: {exc}', flush=True)
                continue
            saved.update(found)
            checked += 1
            matched += len(found)
            print(f'{checked}/{len(pending)} {author["author_id"]}: {len(found)}', flush=True)
            if checked % 10 == 0:
                OVERRIDES.write_text(json.dumps(saved, ensure_ascii=False, indent=2) + "\n")
    OVERRIDES.write_text(json.dumps(saved, ensure_ascii=False, indent=2) + "\n")
    print(f"checked {checked} authors / matched {matched} works / saved {len(saved)} overrides")


if __name__ == "__main__":
    main()
