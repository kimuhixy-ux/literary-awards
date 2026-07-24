#!/usr/bin/env python3
"""Wikidata作品IDから多言語のラベル・別名を取得する。"""
import json
import time
import urllib.parse
import urllib.request
import urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
WORKS = DATA / "major_works.json"
OUTPUT = DATA / "work_aliases.json"
API = "https://www.wikidata.org/w/api.php"
LANGUAGES = "ja|en|zh|zh-hans|zh-hant|ko|ru|uk|be|bg|sr|ar|he|fa|hi|bn|ur|fr|es|pt|de|it|pl|cs|sk|hu|ro|nl|sv|no|da|fi|is|el|tr|id|ms|vi|th"


def chunks(values, size=50):
    for start in range(0, len(values), size):
        yield values[start:start + size]


def qid(work):
    for url in work.get("source_urls", []):
        if "wikidata.org/wiki/Q" in url:
            return url.rsplit("/", 1)[-1]
    return None


def main():
    works = json.loads(WORKS.read_text())
    ids = sorted({value for rows in works.values() for work in rows if (value := qid(work))})
    saved = json.loads(OUTPUT.read_text()) if OUTPUT.exists() else {}
    pending = [value for value in ids if value not in saved]
    for number, batch in enumerate(chunks(pending), 1):
        params = {
            "action": "wbgetentities", "format": "json", "formatversion": 2,
            "ids": "|".join(batch), "props": "labels|aliases", "languages": LANGUAGES,
        }
        req = urllib.request.Request(API + "?" + urllib.parse.urlencode(params), headers={
            "User-Agent": "literary-awards-bibliography/3.0"
        })
        for attempt in range(6):
            try:
                with urllib.request.urlopen(req, timeout=60) as response:
                    entities = json.load(response).get("entities", {})
                break
            except urllib.error.HTTPError as exc:
                if exc.code != 429 or attempt == 5:
                    raise
                delay = 5 * (attempt + 1)
                print(f"rate limited; retrying in {delay}s", flush=True)
                time.sleep(delay)
        for entity_id in batch:
            entity = entities.get(entity_id, {})
            values = [x.get("value") for x in entity.get("labels", {}).values()]
            values += [x.get("value") for rows in entity.get("aliases", {}).values() for x in rows]
            saved[entity_id] = list(dict.fromkeys(x for x in values if x))
        if number % 10 == 0:
            OUTPUT.write_text(json.dumps(saved, ensure_ascii=False, indent=2) + "\n")
        print(f"{min(number * 50, len(pending))}/{len(pending)}", flush=True)
        time.sleep(1.25)
    OUTPUT.write_text(json.dumps(saved, ensure_ascii=False, indent=2) + "\n")
    print(f"saved {len(saved)} work entities")


if __name__ == "__main__":
    main()
