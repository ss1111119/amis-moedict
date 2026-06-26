#!/usr/bin/env python3
# coding: utf-8
# 從字典挑出「可能是地名/部落」的詞條，列出 stem、定義，並粗提取中文地名候選
import json, re, sys
from pathlib import Path

DOCS_S = Path("docs/s")
SKIP = {"ch-mapping.json", "ch-mapping-smart.json", "ch-mapping-new.json",
        "index.json", "stem-words.json"}
OUT = Path("placenames.tsv")

# 地名訊號
SIG_STRONG = re.compile(r"部落名稱|社名|地名|部落集會所")          # 明確標記
SIG_ADMIN  = re.compile(r"[縣市鄉鎮][一-鿿]{0,4}[鄉鎮市區村里]")  # 行政區串
SIG_TODAY  = re.compile(r"今[台臺]?[灣]?")                          # 「今台灣…」
SIG_WORD   = re.compile(r"部落|村落|社區")

# 從定義抽中文地名候選：「今…X村/里/部落/地區」「XX部落」
def extract_places(d):
    cands = set()
    # 行政區尾：抓 …鄉/鎮/市/村/里/區 結尾的 2-7 字詞
    for m in re.finditer(r"[一-鿿]{2,7}(?:村|里|鄉|鎮|市|區|部落|社)", d):
        w = m.group(0)
        if not re.search(r"名稱|地區$", w):
            cands.add(w)
    return cands


rows = []
for fn in sorted(DOCS_S.glob("*.json")):
    if fn.name in SKIP:
        continue
    try:
        j = json.loads(fn.read_text())
    except:
        continue
    if not isinstance(j, dict):
        continue
    stem = j.get("t") or j.get("stem", "")
    if not stem:
        continue
    defs = [d.get("f","") for h in j.get("h",[]) for d in h.get("d",[]) if d.get("f","")]
    blob = "；".join(defs)
    if not blob:
        continue

    strong = bool(SIG_STRONG.search(blob))
    admin  = bool(SIG_ADMIN.search(blob))
    today  = bool(SIG_TODAY.search(blob))
    word   = bool(SIG_WORD.search(blob))
    # 判定：有明確標記，或（行政區串 + 今/部落字樣）
    is_place = strong or (admin and (today or word))
    if not is_place:
        continue

    tag = "強" if strong else "弱"
    places = "、".join(sorted(extract_places(blob))) or "(無)"
    rows.append((tag, stem, blob[:60], places))

rows.sort(key=lambda r: (r[0] != "強", r[1]))
with open(OUT, "w", encoding="utf-8") as f:
    f.write("標記\tstem\t定義\t中文地名候選\n")
    for tag, stem, d, places in rows:
        f.write(f"{tag}\t{stem}\t{d}\t{places}\n")

n_strong = sum(1 for r in rows if r[0] == "強")
print(f"共挑出 {len(rows)} 個（明確標記 {n_strong}，弱訊號 {len(rows)-n_strong}）\n")
for tag, stem, d, places in rows:
    print(f"[{tag}] {stem}")
    print(f"     定義: {d}")
    print(f"     地名候選: {places}")
print(f"\n完整清單已存 {OUT}", file=sys.stderr)
