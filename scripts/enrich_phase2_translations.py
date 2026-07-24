#!/usr/bin/env python3
"""NDL SearchでPhase 2受賞作の邦訳書誌を厳格照合する。

原題と著者姓が同一レコード内で一致した場合だけ採用する。結果は
data/phase2_translations.json に保存し、--apply で受賞データへ反映する。
"""
import argparse
import json
import re
import time
import unicodedata
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from lxml import etree

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
AWARDS = ("goncourt", "pulitzer-fiction", "national-book")
OVERRIDES = DATA / "phase2_translations.json"
SRU = "https://ndlsearch.ndl.go.jp/api/sru"


def norm(value):
    value = unicodedata.normalize("NFKC", value or "").casefold()
    return re.sub(r"[^0-9a-z\u00c0-\u024f\u3040-\u30ff\u3400-\u9fff]", "", value)


def local(tag):
    return tag.rsplit("}", 1)[-1]


def text(node):
    return " ".join("".join(node.itertext()).split())


def parse_records(payload):
    outer = etree.fromstring(payload, etree.XMLParser(recover=True))
    for rd in outer.xpath("//*[local-name()='recordData']"):
        raw = rd.text or ""
        inner = etree.fromstring(raw.encode(), etree.XMLParser(recover=True))
        resources = inner.xpath("//*[local-name()='BibResource']")
        if not resources:
            continue
        resource = resources[0]
        direct = list(resource)
        def vals(name):
            values = []
            for node in direct:
                if local(node.tag) != name:
                    continue
                value = (node.text or "").strip() or text(node)
                if value:
                    values.append(value)
            return values
        descriptions = vals("description")
        originals = vals("alternative") + [
            x.split(":", 1)[1].strip() for x in descriptions if x.startswith("原タイトル:")
        ]
        creators = vals("creator")
        admins = inner.xpath("//*[local-name()='BibAdminResource']")
        url = admins[0].get("{http://www.w3.org/1999/02/22-rdf-syntax-ns#}about") if admins else None
        yield {
            "title": (vals("title") or [None])[0],
            "originals": originals,
            "creators": creators,
            "publisher": (vals("publisher") or [None])[0],
            "year": (lambda m: int(m.group()) if m else None)(
                re.search(r"(?:18|19|20)\d{2}", (vals("issued") or [""])[0])
            ),
            "url": url,
        }


def lookup(work, author):
    surname = (author or "").split()[-1]
    query = f'title="{work}" AND creator="{surname}"'
    url = SRU + "?" + urllib.parse.urlencode({
        "operation": "searchRetrieve", "version": "1.2", "recordSchema": "dcndl",
        "maximumRecords": 20, "query": query,
    })
    req = urllib.request.Request(url, headers={"User-Agent": "literary-awards-bibliography/1.0"})
    with urllib.request.urlopen(req, timeout=30) as response:
        candidates = list(parse_records(response.read()))
    exact = []
    for item in candidates:
        original_match = any(norm(x) == norm(work) for x in item["originals"])
        author_match = any(norm(surname) in norm(x) for x in item["creators"])
        if "中国" in (item["publisher"] or ""):
            continue
        translators = []
        for creator in item["creators"]:
            m = re.search(r"([^;；,，]+?)\s*訳(?:$|[\s,，])", creator)
            if m:
                translators.append(m.group(1).strip())
        if original_match and author_match and item["title"] and item["publisher"] and translators:
            item["translator"] = "・".join(dict.fromkeys(translators))
            exact.append(item)
    exact.sort(key=lambda x: (x["year"] or 9999, len(x["title"] or "")))
    return exact[0] if exact else None


def key(award, row):
    return f"{award}:{row['year']}:{row.get('author_id') or '-'}"


def fetch(limit=None):
    saved = json.loads(OVERRIDES.read_text()) if OVERRIDES.exists() else {}
    pending = []
    for award in AWARDS:
        path = DATA / "laureates" / f"{award}.json"
        for row in json.loads(path.read_text()):
            if not row.get("work_original") or not row.get("author_en"):
                continue
            record_key = key(award, row)
            if record_key in saved:
                continue
            if limit is not None and len(pending) >= limit:
                break
            pending.append((record_key, row["work_original"], row["author_en"]))
        if limit is not None and len(pending) >= limit:
            break

    def one(item):
        record_key, work, author = item
        return record_key, lookup(work, author)

    checked = 0
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(one, item): item[0] for item in pending}
        for future in as_completed(futures):
            record_key = futures[future]
            try:
                _, hit = future.result()
            except Exception as exc:
                print(f"ERROR {record_key}: {exc}")
                continue
            saved[record_key] = None if hit is None else {
                "status": "available", "title_ja": hit["title"],
                "translator": hit["translator"], "publisher": hit["publisher"],
                "year": hit["year"], "note": "国立国会図書館サーチで書誌確認",
                "source_url": hit["url"],
            }
            checked += 1
            print(f"{record_key}: {hit['title'] if hit else '-'}")
            if checked % 10 == 0:
                OVERRIDES.write_text(json.dumps(saved, ensure_ascii=False, indent=2) + "\n")
    OVERRIDES.write_text(json.dumps(saved, ensure_ascii=False, indent=2) + "\n")


def apply():
    saved = json.loads(OVERRIDES.read_text())
    count = 0
    for award in AWARDS:
        path = DATA / "laureates" / f"{award}.json"
        rows = json.loads(path.read_text())
        for row in rows:
            override = saved.get(key(award, row))
            if not override:
                continue
            source = override.get("source_url")
            cleaned = {k: v for k, v in override.items() if k != "source_url"}
            # NDLの構造化項目をプレーンテキスト化した際に付く読み・所在地を除く。
            publisher = cleaned.get("publisher") or ""
            publisher = re.split(r"\s+(?=[ァ-ヶー]{3,}(?:\s|$))", publisher)[0]
            publisher = re.sub(r"\s+(東京|京都|大阪|北京)$", "", publisher)
            cleaned["publisher"] = publisher
            translator = cleaned.get("translator") or ""
            cleaned["translator"] = re.split(r"[;；]", translator)[-1].strip()
            row["jp_translation"] = cleaned
            if source and source not in row["source_urls"]:
                row["source_urls"].append(source)
            count += 1
        path.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n")
    print(f"applied: {count}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--fetch", action="store_true")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()
    if args.fetch:
        fetch(args.limit)
    if args.apply:
        apply()
