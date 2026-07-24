# -*- coding: utf-8 -*-
# data/authors.json を data/laureates/*.json と data/major_works.json から再生成するスクリプト。
# 実行: python3 scripts/gen_authors.py (リポジトリルートから)
import json, collections, os

BASE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")

AWARD_FILES = {
    "nobel": "laureates/nobel.json",
    "booker": "laureates/booker.json",
    "intl-booker": "laureates/intl-booker.json",
    "akutagawa": "laureates/akutagawa.json",
    "goncourt": "laureates/goncourt.json",
    "pulitzer-fiction": "laureates/pulitzer-fiction.json",
    "national-book": "laureates/national-book.json",
    "cervantes": "laureates/cervantes.json",
}

with open(f"{BASE}/major_works.json", encoding="utf-8") as f:
    MAJOR_WORKS = json.load(f)

authors = collections.OrderedDict()

for award_id, path in AWARD_FILES.items():
    with open(f"{BASE}/{path}", encoding="utf-8") as f:
        records = json.load(f)
    for r in records:
        aid = r.get("author_id")
        if not aid:
            continue  # no-award year placeholder
        if aid not in authors:
            authors[aid] = {
                "author_id": aid,
                "name_ja": r.get("author_ja"),
                "name_en": r.get("author_en"),
                "country": r.get("country"),
                "awards": []
            }
        entry = {
            "award_id": award_id,
            "year": r.get("year"),
        }
        if award_id == "akutagawa":
            entry["session"] = r.get("session")
            entry["round"] = r.get("round")
        if r.get("work_ja"):
            entry["work_ja"] = r.get("work_ja")
        if r.get("work_original"):
            entry["work_original"] = r.get("work_original")
        if r.get("theme_summary_ja"):
            entry["theme_summary_ja"] = r.get("theme_summary_ja")
        jpt = r.get("jp_translation") or {}
        if jpt.get("status"):
            entry["jp_translation_status"] = jpt["status"]
            if jpt.get("title_ja"):
                entry["jp_translation_title"] = jpt["title_ja"]
        authors[aid]["awards"].append(entry)
        # prefer a non-null name_en/country if found later (e.g. akutagawa entries lack author_en)
        if not authors[aid]["name_en"] and r.get("author_en"):
            authors[aid]["name_en"] = r.get("author_en")
        if not authors[aid]["country"] and r.get("country"):
            authors[aid]["country"] = r.get("country")

# build representative_works: unique works across all award entries, in chronological order
records_out = []
for aid, a in authors.items():
    a["awards"].sort(key=lambda e: e["year"])
    award_ids = sorted(set(e["award_id"] for e in a["awards"]))
    a["is_multi_award"] = len(award_ids) > 1
    a["award_ids"] = award_ids
    works = []
    seen = set()
    for e in a["awards"]:
        w = e.get("work_ja") or e.get("work_original")
        if w and w not in seen:
            seen.add(w)
            works.append({
                "work_ja": e.get("work_ja"),
                "work_original": e.get("work_original"),
                "award_id": e["award_id"],
                "year": e["year"],
                "jp_translation_status": e.get("jp_translation_status"),
                "jp_translation_title": e.get("jp_translation_title"),
                "theme_summary_ja": e.get("theme_summary_ja"),
            })
    a["representative_works"] = works
    if aid in MAJOR_WORKS:
        a["major_works"] = MAJOR_WORKS[aid]
    records_out.append(a)

multi = [a for a in records_out if a["is_multi_award"]]
print(f"total unique authors: {len(records_out)}")
print(f"multi-award authors: {len(multi)}")
for a in multi:
    print(" -", a["author_id"], a["award_ids"])

with open(f"{BASE}/authors.json", "w", encoding="utf-8") as f:
    json.dump(records_out, f, ensure_ascii=False, indent=2)
