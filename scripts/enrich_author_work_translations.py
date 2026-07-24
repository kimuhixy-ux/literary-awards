#!/usr/bin/env python3
"""全登録作家の受賞作以外について、NDL Searchで邦訳書誌を一括照合する。"""
import argparse
import hashlib
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
WORK_ALIASES = DATA / "work_aliases.json"
DIRECT_CHECKS = DATA / "author_work_translation_checks.json"


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


def search(title, author):
    query = f'title="{title}" AND creator="{author}"'
    url = SRU + "?" + urllib.parse.urlencode({
        "operation": "searchRetrieve", "version": "1.2", "recordSchema": "dcndl",
        "maximumRecords": 50, "mediatype": "books", "query": query,
    })
    req = urllib.request.Request(url, headers={"User-Agent": "literary-awards-bibliography/3.0"})
    with urllib.request.urlopen(req, timeout=45) as response:
        return list(parse_records(response.read()))


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


def unique(values):
    return list(dict.fromkeys(value for value in values if value))


def work_qid(work):
    for url in work.get("source_urls", []):
        if "wikidata.org/wiki/Q" in url:
            return url.rsplit("/", 1)[-1]
    return None


def work_titles(work, aliases):
    qid = work_qid(work)
    return unique([work.get("title_original"), work.get("title_ja"), *(aliases.get(qid, []) if qid else [])])


def ranked_titles(work, aliases):
    titles = work_titles(work, aliases)
    preferred = [work.get("title_original"), work.get("title_ja")]
    cjk = [x for x in titles if re.search(r"[\u3040-\u30ff\u3400-\u9fff]", x)]
    return unique([*preferred, *cjk, *titles])[:6]


def title_matches(wanted, actual):
    wanted_norm, actual_norm = norm(wanted), norm(actual)
    if wanted_norm == actual_norm:
        return True
    minimum = 3 if re.search(r"[\u3040-\u30ff\u3400-\u9fff]", wanted) else 5
    return len(wanted_norm) >= minimum and wanted_norm in actual_norm


def check_author(author, works, aliases):
    names = unique([author.get("name_ja"), author.get("name_en")])
    if not names:
        return {}
    records = []
    for name in names:
        records.extend(bibliography(name))
    by_title = {}
    for item in records:
        creator_blob = norm(" ".join(item["creators"]))
        if not any(norm(name) in creator_blob or norm(name.split()[-1]) in creator_blob for name in names):
            continue
        translator = translators(item["creators"])
        if not item.get("title") or not item.get("publisher") or not translator:
            continue
        for title in [item["title"], *item["originals"]]:
            by_title.setdefault(norm(title), []).append((item, translator))
    found = {}
    for work in works:
        if (work.get("jp_translation") or {}).get("status") != "unverified":
            continue
        hits = []
        for title in work_titles(work, aliases):
            hits.extend(by_title.get(norm(title), []))
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


def check_work(author, work, aliases):
    names = unique([author.get("name_ja"), author.get("name_en")])
    titles = ranked_titles(work, aliases)
    creator_norms = [norm(name) for name in names] + [norm(name.split()[-1]) for name in names]
    for title in titles:
        for name in names:
            for item in search(title, name):
                creator_blob = norm(" ".join(item["creators"]))
                if not any(value and value in creator_blob for value in creator_norms):
                    continue
                translator = translators(item["creators"])
                if not item.get("title") or not item.get("publisher") or not translator:
                    continue
                record_titles = [item["title"], *item["originals"]]
                if not any(title_matches(wanted, actual) for wanted in titles for actual in record_titles):
                    continue
                return {
                    "status": "available", "title_ja": item["title"], "translator": translator,
                    "publisher": clean_publisher(item["publisher"]), "year": item.get("year"),
                    "note": "国立国会図書館サーチで書誌確認", "source_url": item.get("url"),
                }
    return None


def fingerprint(author, work, aliases):
    payload = json.dumps({
        "algorithm": 3,
        "names": unique([author.get("name_ja"), author.get("name_en")]),
        "titles": ranked_titles(work, aliases),
    }, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--author-id", action="append", default=[])
    parser.add_argument("--direct", action="store_true")
    parser.add_argument("--japanese-title-only", action="store_true")
    args = parser.parse_args()
    authors = json.loads(AUTHORS.read_text())
    works = json.loads(WORKS.read_text())
    saved = json.loads(OVERRIDES.read_text()) if OVERRIDES.exists() else {}
    aliases = json.loads(WORK_ALIASES.read_text()) if WORK_ALIASES.exists() else {}
    checks = json.loads(DIRECT_CHECKS.read_text()) if DIRECT_CHECKS.exists() else {}
    pending = [a for a in authors if any(
        (w.get("jp_translation") or {}).get("status") == "unverified"
        for w in works.get(a["author_id"], [])
    )]
    if args.author_id:
        wanted = set(args.author_id)
        pending = [a for a in pending if a["author_id"] in wanted]
    if args.limit:
        pending = pending[:args.limit]
    if args.direct:
        jobs = []
        for author in pending:
            for work in works[author["author_id"]]:
                if (work.get("jp_translation") or {}).get("status") != "unverified":
                    continue
                if args.japanese_title_only and not work.get("title_ja"):
                    continue
                key = f'{author["author_id"]}:{work["title_original"]}'
                mark = fingerprint(author, work, aliases)
                if checks.get(key) == mark:
                    continue
                jobs.append((key, mark, author, work))
        if args.limit:
            jobs = jobs[:args.limit]
        checked = matched = 0
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            futures = {pool.submit(check_work, author, work, aliases): (key, mark)
                       for key, mark, author, work in jobs}
            for future in as_completed(futures):
                key, mark = futures[future]
                try:
                    hit = future.result()
                except Exception as exc:
                    print(f"ERROR {key}: {exc}", flush=True)
                    continue
                checks[key] = mark
                checked += 1
                if hit:
                    saved[key] = hit
                    matched += 1
                print(f"{checked}/{len(jobs)} {key}: {'hit' if hit else '-'}", flush=True)
                if checked % 10 == 0:
                    OVERRIDES.write_text(json.dumps(saved, ensure_ascii=False, indent=2) + "\n")
                    DIRECT_CHECKS.write_text(json.dumps(checks, ensure_ascii=False, indent=2) + "\n")
        OVERRIDES.write_text(json.dumps(saved, ensure_ascii=False, indent=2) + "\n")
        DIRECT_CHECKS.write_text(json.dumps(checks, ensure_ascii=False, indent=2) + "\n")
        print(f"direct checked {checked} works / matched {matched} / saved {len(saved)} overrides")
        return

    checked = matched = 0
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(check_author, author, works[author["author_id"]], aliases): author for author in pending}
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
