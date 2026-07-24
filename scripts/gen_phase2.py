#!/usr/bin/env python3
"""Wikipediaの歴代受賞表からPhase 2の4賞JSONを生成する。

公式サイトで最新年を照合したうえで使用すること。既存authors.jsonのauthor_idを
英語名で名寄せし、同一作家の賞横断関連を維持する。
"""
import json, re, unicodedata
from pathlib import Path
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]; DATA=ROOT/"data"; OUT=DATA/"laureates"
PAGES={"goncourt":"https://en.wikipedia.org/wiki/Prix_Goncourt","pulitzer":"https://en.wikipedia.org/wiki/Pulitzer_Prize_for_Fiction","national":"https://en.wikipedia.org/wiki/National_Book_Award_for_Fiction","cervantes":"https://en.wikipedia.org/wiki/Miguel_de_Cervantes_Prize"}
OFFICIAL={"goncourt":"https://www.academiegoncourt.com/","pulitzer":"https://www.pulitzer.org/prize-categories/fiction","national":"https://www.nationalbook.org/awards-prizes/national-book-awards-2025/","cervantes":"https://www.cultura.gob.es/cultura/areas/libro/mc/premio-cervantes.html"}
LOCAL={"goncourt":"/tmp/goncourt.html","pulitzer":"/tmp/pulitzer.html","national":"/tmp/national.html","cervantes":"/tmp/cervantes.html"}

def clean(v):
    if pd.isna(v): return None
    s=re.sub(r"\[[^]]*]","",str(v)); s=re.sub(r"\s+"," ",s).strip()
    return None if s in {"","nan","—N/a","N/a"} else s

def key(v):
    v=unicodedata.normalize("NFKD",v or "").encode("ascii","ignore").decode().lower()
    return re.sub(r"[^a-z0-9]","",v)

existing=json.loads((DATA/"authors.json").read_text()); by_name={}
for a in existing:
    if a.get("name_en"): by_name.setdefault(key(a["name_en"]),a)
used={a["author_id"] for a in existing}
def identity(name):
    hit=by_name.get(key(name))
    if hit: return hit["author_id"],hit.get("name_ja") or name,hit.get("country")
    base=unicodedata.normalize("NFKD",name).encode("ascii","ignore").decode().lower()
    base=re.sub(r"[^a-z0-9]+","-",base).strip("-") or "author"
    aid=base; n=2
    while aid in used: aid=f"{base}-{n}"; n+=1
    used.add(aid); by_name[key(name)]={"author_id":aid,"name_ja":name,"country":None}; return aid,name,None

COUNTRIES={"Spain":"スペイン","Mexico":"メキシコ","Argentina":"アルゼンチン","Cuba":"キューバ","Uruguay":"ウルグアイ","Paraguay":"パラグアイ","Peru":"ペルー","Chile":"チリ","Colombia":"コロンビア","Venezuela":"ベネズエラ","Nicaragua":"ニカラグア"}
def translation(work):
    if not work: return {"status":"n/a","title_ja":None,"translator":None,"publisher":None,"year":None,"note":"対象作品なし"}
    return {"status":"unavailable","title_ja":None,"translator":None,"publisher":None,"year":None,"note":"暫定値。邦訳の有無・書誌は要確認（未邦訳を意味しない）"}

def record(year,name,work,award,country,language,notes=None):
    if not name or name.lower().startswith("not awarded"):
        return {"year":year,"session":None,"author_id":None,"author_ja":"該当なし","author_en":None,"country":None,"language":None,"work_ja":None,"work_original":None,"citation_ja":None,"lecture_title":None,"lecture_url":None,"jp_translation":translation(None),"source_urls":[OFFICIAL[award],PAGES[award]],"notes":notes or "該当なし","theme_summary_ja":None}
    aid,ja,known_country=identity(name)
    return {"year":year,"session":None,"author_id":aid,"author_ja":ja,"author_en":name,"country":known_country or country,"language":language,"work_ja":None,"work_original":work,"citation_ja":None,"lecture_title":None,"lecture_url":None,"jp_translation":translation(work),"source_urls":[OFFICIAL[award],PAGES[award]],"notes":notes,"theme_summary_ja":None}

def tables(name): return pd.read_html(LOCAL[name] if Path(LOCAL[name]).exists() else PAGES[name])

# Prix Goncourt: 年ごとに1作品。1906年のみ兄弟2名の共同名義を別レコード化。
g=[]
for _,r in tables("goncourt")[1].iterrows():
    if pd.isna(r["Year"]): continue
    year=int(r["Year"]); author=clean(r["Author"]); work=clean(r["French title"])
    names=["Jean Tharaud","Jérôme Tharaud"] if year==1906 else [author]
    for name in names: g.append(record(year,name,work,"goncourt","フランス","フランス語","共同受賞" if len(names)>1 else None))

# Pulitzer: 表では同一年の先頭行が受賞、後続行がfinalist。該当なしも先頭行に残る。
p=[]; pt=tables("pulitzer")[2]; pt=pt[pt["Year"].notna()]
for year,group in pt.groupby(pt["Year"].astype(int),sort=True):
    r=group.iloc[0]; p.append(record(int(year),clean(r["Author"]),clean(r["Work"]),"pulitzer","アメリカ","英語"))

# National Book Award: Result=Winnerのみ。1980〜83年の部門分割による複数受賞も保持。
n=[]
for t in tables("national")[1:10]:
    if "Result" not in t: continue
    for _,r in t[t["Result"].astype(str).str.contains("Winner",case=False,na=False)].iterrows():
        m=re.search(r"\d{4}",str(r["Year"]));
        if m: n.append(record(int(m.group()),clean(r["Author"]),clean(r["Title"]),"national","アメリカ","英語",f"部門: {clean(r.get('Category'))}" if clean(r.get("Category")) else None))
n.sort(key=lambda x:(x["year"],x.get("author_en") or ""))

# Cervantes Prize: 作家の全業績への賞なので対象作品なし。1979年の共同受賞も表の2行を保持。
c=[]
for _,r in tables("cervantes")[1].iterrows():
    m=re.search(r"\d{4}",str(r["Year"]));
    if not m: continue
    country=COUNTRIES.get(clean(r["Country"]),clean(r["Country"])); c.append(record(int(m.group()),clean(r["Winner"]),None,"cervantes",country,"スペイン語","全業績への授賞"))

for name,rows in [("goncourt",g),("pulitzer-fiction",p),("national-book",n),("cervantes",c)]:
    (OUT/f"{name}.json").write_text(json.dumps(rows,ensure_ascii=False,indent=2)+"\n")
    print(f"{name}: {len(rows)} records, {min(x['year'] for x in rows)}-{max(x['year'] for x in rows)}")
print("邦訳書誌を再適用するには: python3 scripts/enrich_phase2_translations.py --apply")
