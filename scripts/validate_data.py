#!/usr/bin/env python3
"""全賞データの件数・形式・作家ID名寄せを検証する。"""
import collections, json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; DATA=ROOT/"data"
awards=json.loads((DATA/"awards.json").read_text()); errors=[]; names=collections.defaultdict(set)
expected={"nobel":(129,1901,2025),"booker":(60,1969,2025),"intl-booker":(17,2005,2026),"akutagawa":(222,1935,2026),"goncourt":(124,1903,2025),"pulitzer-fiction":(109,1918,2026),"national-book":(83,1950,2025),"cervantes":(51,1976,2025)}
required={"year","author_id","author_ja","work_original","jp_translation","source_urls"}; statuses={"available","unavailable","original-ja","n/a"}
for award in awards:
    path=award.get("data_file")
    if not path: errors.append(f"{award['id']}: data_file missing"); continue
    rows=json.loads((DATA/path).read_text()); years=[r["year"] for r in rows]; exp=expected[award["id"]]
    if (len(rows),min(years),max(years))!=exp: errors.append(f"{award['id']}: expected {exp}, got {(len(rows),min(years),max(years))}")
    for i,r in enumerate(rows):
        missing=required-r.keys()
        if missing: errors.append(f"{award['id']}[{i}]: missing {sorted(missing)}")
        if (r.get("jp_translation") or {}).get("status") not in statuses: errors.append(f"{award['id']}[{i}]: bad translation status")
        if r.get("author_en") and r.get("author_id"): names[r["author_en"]].add(r["author_id"])
        if r.get("citation_ja") and not r["citation_ja"].endswith("(要旨)"): errors.append(f"{award['id']}[{i}]: citation is not marked summary")
duplicates={name:ids for name,ids in names.items() if len(ids)>1}
if duplicates: errors.append(f"same author has multiple ids: {duplicates}")
authors=json.loads((DATA/"authors.json").read_text()); print(f"8 awards / {sum(x[0] for x in expected.values())} records / {len(authors)} authors / {sum(a['is_multi_award'] for a in authors)} multi-award authors")
if errors:
    print("\n".join("ERROR: "+e for e in errors)); raise SystemExit(1)
print("validation: OK")
