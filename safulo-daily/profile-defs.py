#!/usr/bin/env python3
# coding: utf-8
# 掃描全部詞條定義，按結構特徵分桶統計，了解真實句型多樣性
# 不跑 LLM，純文字分析
import json, re, sys
from pathlib import Path
from collections import defaultdict

DOCS_S = Path("docs/s")
SKIP = {"ch-mapping.json", "ch-mapping-smart.json", "ch-mapping-new.json",
        "index.json", "stem-words.json"}
SKIP_PREFIXES = ("要","指","〔","即將","將要","把","去","在","也","可以",
                 "讓","用來","使","被","當","請","表示")

# 收集 (stem, 第一條定義) — 與主腳本一致的篩選
items = []
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
    defs = []
    for h in j.get("h", []):
        for d in h.get("d", []):
            f = d.get("f", "")
            if f and not f.startswith(SKIP_PREFIXES):
                defs.append(f)
    if defs:
        items.append((stem, "；".join(defs[:2])))

n = len(items)
print(f"母體：{n} 個詞條\n")

# 特徵分桶（一個定義可落入多桶）
features = {
    "含「的」短語":        lambda d: "的" in d,
    "含括號（）/()":       lambda d: bool(re.search(r"[（(].*?[）)]", d)),
    "多義項（含；）":      lambda d: "；" in d,
    "含頓號、":            lambda d: "、" in d,
    "含地名後綴(縣市鄉鎮村)": lambda d: bool(re.search(r"[縣市鄉鎮村]", d)),
    "部落/社名":           lambda d: ("部落" in d or "社名" in d or "地名" in d),
    "前綴/後綴/短語標記":   lambda d: bool(re.search(r"前綴|後綴|短語|疊詞|語助", d)),
    "含省略號…/—":         lambda d: bool(re.search(r"[…—\.]{2,}|…", d)),
    "含人名/姓氏":         lambda d: bool(re.search(r"人名|姓氏|名字", d)),
    "祈使/促使/命令":       lambda d: bool(re.search(r"促使|命令|祈使|表.*使", d)),
}
buckets = defaultdict(list)
for stem, d in items:
    for name, pred in features.items():
        if pred(d):
            buckets[name].append((stem, d))

print("===== 特徵分布 =====")
for name in features:
    hits = buckets[name]
    print(f"{name:22s} {len(hits):6d}  ({len(hits)/n*100:5.1f}%)")

# 長度分布
import bisect
lens = sorted(len(d) for _, d in items)
def pct(p): return lens[int(len(lens)*p)]
print(f"\n定義長度：min={lens[0]} p25={pct(.25)} 中位={pct(.5)} p75={pct(.75)} p95={pct(.95)} max={lens[-1]}")

# 各類列 4 個例子
print("\n===== 各類樣本（前 4）=====")
for name in features:
    print(f"\n--- {name} ---")
    for stem, d in buckets[name][:4]:
        print(f"  {stem} | {d[:50]}")
