#!/usr/bin/env python3
"""蔵書Vault(iCloud Obsidian)と受賞作データを照合し、data/owned.jsonとowned-report.mdを生成する。

読み取り専用。vaultへの書き込みは一切行わない。
"""
import json
import os
import re
import unicodedata
import difflib
from pathlib import Path
from collections import defaultdict

REPO = Path(__file__).resolve().parent.parent
VAULT_BOOKS = Path(
    "/Users/user/Library/Mobile Documents/iCloud~md~obsidian/Documents/蔵書Vault/03_書籍"
)

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

NOISE_CHARS = "『』「」【】（）()[]｛｝{}:：・、。,.!!??\"'　 \t\n―ー—–-−／/'"


def normalize(s):
    if not s:
        return ""
    s = unicodedata.normalize("NFKC", s)
    for ch in NOISE_CHARS:
        s = s.replace(ch, "")
    return s.lower().strip()


VOLUME_PAREN_RE = re.compile(r"[（(][^（）()]{0,6}[）)]\s*$")
VOLUME_SUFFIX_RE = re.compile(r"(改版|新版|文庫版|愛蔵版|決定版|新装版|完全版)+$")
VOLUME_BARE_RE = re.compile(r"[\s　]+(上|中|下|前編|後編|正|続|\d{1,2})\s*$")


def core_title(raw):
    s = raw
    prev = None
    while prev != s:
        prev = s
        s = VOLUME_PAREN_RE.sub("", s).strip()
        s = VOLUME_SUFFIX_RE.sub("", s).strip()
        s = VOLUME_BARE_RE.sub("", s).strip()
    return normalize(s)


def load_json(rel):
    return json.loads((REPO / "data" / rel).read_text(encoding="utf-8"))


def load_catalog():
    """蔵書Vault/03_書籍の全.mdからtitle/authorをfrontmatterから抽出する。"""
    catalog = []
    unreadable = []
    for fn in sorted(os.listdir(VAULT_BOOKS)):
        if not fn.endswith(".md"):
            continue
        p = VAULT_BOOKS / fn
        try:
            text = p.read_text(encoding="utf-8")
        except Exception as e:
            unreadable.append({"file": fn, "error": str(e)})
            continue
        m = re.match(r"^---\n(.*?)\n---", text, re.S)
        title = None
        author = None
        if m:
            fm = m.group(1)
            tm = re.search(r'^title:\s*"?(.*?)"?\s*$', fm, re.M)
            am = re.search(r'^author:\s*"?(.*?)"?\s*$', fm, re.M)
            if tm:
                title = tm.group(1).strip()
            if am:
                author = am.group(1).strip()
        if not title:
            title = fn[:-3]
        catalog.append(
            {
                "title": title,
                "title_norm": normalize(title),
                "title_core": core_title(title),
                "author": author or "",
                "author_norm": normalize(author or ""),
                "path": str(p.relative_to(VAULT_BOOKS.parent.parent)),
            }
        )
    return catalog, unreadable


def build_indexes(catalog):
    by_norm = defaultdict(list)
    by_core = defaultdict(list)
    for e in catalog:
        by_norm[e["title_norm"]].append(e)
        by_core[e["title_core"]].append(e)
    return by_norm, by_core


def find_match(candidates, author_ja, author_en, by_norm, by_core, catalog):
    """candidates: [(title, source)] 優先順で試す。"""
    author_norm = normalize(author_ja)
    author_en_norm = normalize(author_en)

    for title, source in candidates:
        if not title:
            continue
        t_norm = normalize(title)
        t_core = core_title(title)
        if not t_norm:
            continue
        if t_norm in by_norm:
            e = by_norm[t_norm][0]
            return {
                "status": "exact",
                "vault_path": e["path"],
                "matched_title": e["title"],
                "matched_source": source,
                "matched_candidate": title,
            }
        if t_core and t_core in by_core:
            e = by_core[t_core][0]
            return {
                "status": "exact",
                "vault_path": e["path"],
                "matched_title": e["title"],
                "matched_source": source,
                "matched_candidate": title,
            }

    # fuzzy pass: edit-distance ratio, or author match + title substring
    best = None
    best_ratio = 0.0
    for title, source in candidates:
        if not title:
            continue
        t_norm = normalize(title)
        if len(t_norm) < 2:
            continue
        for e in catalog:
            if not e["title_norm"]:
                continue
            # author-corroborated substring match
            if author_norm and len(author_norm) >= 2 and author_norm in e["author_norm"]:
                if len(t_norm) >= 3 and e["title_core"] and (t_norm in e["title_norm"] or e["title_core"] in t_norm):
                    return {
                        "status": "fuzzy",
                        "vault_path": e["path"],
                        "matched_title": e["title"],
                        "matched_source": source,
                        "matched_candidate": title,
                        "note": "著者一致+書名部分一致",
                    }
            ratio = difflib.SequenceMatcher(None, t_norm, e["title_norm"]).ratio()
            if ratio > best_ratio and ratio >= 0.82:
                best_ratio = ratio
                best = {
                    "status": "fuzzy",
                    "vault_path": e["path"],
                    "matched_title": e["title"],
                    "matched_source": source,
                    "matched_candidate": title,
                    "note": f"類似度{ratio:.2f}",
                }
    return best


def main():
    authors_by_id = {a["author_id"]: a for a in load_json("authors.json")}
    major_works = load_json("major_works.json")

    catalog, unreadable = load_catalog()
    by_norm, by_core = build_indexes(catalog)
    print(f"蔵書カタログ: {len(catalog)}件 (読み込み失敗 {len(unreadable)}件)")

    owned = {}
    fuzzy_list = []
    total_records = 0
    exact_count = 0
    fuzzy_count = 0

    for award_id, relpath in AWARD_FILES.items():
        records = load_json(relpath)
        for r in records:
            author_id = r.get("author_id")
            if not author_id:
                continue
            total_records += 1
            year = r.get("year")
            key = f"{award_id}|{year}|{author_id}"

            candidates = []
            work_ja = r.get("work_ja")
            jp_title = (r.get("jp_translation") or {}).get("title_ja")
            if work_ja:
                candidates.append((work_ja, "work_ja"))
            if jp_title and jp_title != work_ja:
                candidates.append((jp_title, "jp_translation.title_ja"))

            if not candidates:
                # ノーベル賞など「作家の業績」型: 代表作・主要作品から照合
                a = authors_by_id.get(author_id)
                if a:
                    for w in a.get("representative_works", []):
                        if w.get("work_ja"):
                            candidates.append((w["work_ja"], "representative_works"))
                for w in major_works.get(author_id, []):
                    if w.get("title_ja"):
                        candidates.append((w["title_ja"], "major_works"))

            author_ja = r.get("author_ja", "")
            author_en = r.get("author_en", "")
            match = find_match(candidates, author_ja, author_en, by_norm, by_core, catalog)
            if match:
                owned[key] = {
                    "status": match["status"],
                    "vault_path": match["vault_path"],
                    "matched_title": match["matched_title"],
                }
                if match["status"] == "exact":
                    exact_count += 1
                else:
                    fuzzy_count += 1
                    fuzzy_list.append(
                        {
                            "key": key,
                            "award_id": award_id,
                            "year": year,
                            "author_ja": author_ja,
                            "award_title": match.get("matched_candidate"),
                            "vault_title": match["matched_title"],
                            "vault_path": match["vault_path"],
                            "note": match.get("note", ""),
                        }
                    )

    (REPO / "data" / "owned.json").write_text(
        json.dumps(owned, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    none_count = total_records - exact_count - fuzzy_count
    report_lines = []
    report_lines.append("# 蔵書vault照合レポート\n")
    report_lines.append(f"- 対象受賞レコード数: {total_records}")
    report_lines.append(f"- 蔵書カタログ件数(`蔵書Vault/03_書籍`): {len(catalog)}")
    report_lines.append(f"- 読み込み失敗ファイル数: {len(unreadable)}")
    report_lines.append(f"- 完全一致(exact): {exact_count}")
    report_lines.append(f"- 要確認(fuzzy): {fuzzy_count}")
    report_lines.append(f"- 該当なし(none): {none_count}")
    report_lines.append("")
    if unreadable:
        report_lines.append("## 読み込み失敗ファイル\n")
        for u in unreadable:
            report_lines.append(f"- {u['file']}: {u['error']}")
        report_lines.append("")
    report_lines.append("## 要確認一覧(fuzzy) — vaultノート名 ↔ 受賞作名\n")
    report_lines.append("| 賞 | 年 | 作家 | 受賞作側の表記 | vault側の表記 | 備考 |")
    report_lines.append("|----|----|------|--------------|--------------|------|")
    for f in fuzzy_list:
        report_lines.append(
            f"| {f['award_id']} | {f['year']} | {f['author_ja']} | {f['award_title']} | {f['vault_title']} | {f['note']} |"
        )

    (REPO / "owned-report.md").write_text("\n".join(report_lines), encoding="utf-8")

    print(f"完全一致: {exact_count} / 要確認: {fuzzy_count} / 該当なし: {none_count} (全{total_records}件)")
    print("data/owned.json と owned-report.md を生成しました。")


if __name__ == "__main__":
    main()
