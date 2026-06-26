#!/usr/bin/env python3
# coding: utf-8
# ch-mapping.json 收尾：短語收斂 + 已知詞條修正
import json, re
from pathlib import Path

P = Path("docs/s/ch-mapping.json")
m = json.load(open(P, encoding="utf-8"))
print(f"收尾前：{len(m)} 筆")

# v3 prompt 已在 LLM 端拆掉「的」短語、過濾泛用詞，這裡不再做收斂。

# 併入地名對照表（中文村里/部落名 → 阿美羅馬字）。
# 先跑 build-placename-map.py 產生 placename-map.json。
PM = Path("placename-map.json")
if PM.exists():
    pm = json.load(open(PM, encoding="utf-8"))
    added = 0
    for k, v in pm.items():
        if k not in m:          # 不覆蓋已有通用詞義
            m[k] = v
            added += 1
    print(f"併入地名對照 {len(pm)} 筆，新增 {added} 筆")
else:
    print("[警告] 找不到 placename-map.json，跳過地名對照")

# 強制修正已知詞條指向。
m["小米"] = "panay"
m["稻米"] = "hafay"
m["稻子"] = "hafay"
m["竹林"] = "'aolan"

json.dump(m, open(P, "w", encoding="utf-8"), ensure_ascii=False, indent=4)
print(f"收尾後：{len(m)} 筆")
for kw in ["小米", "稻米", "稻子", "竹林"]:
    print(f"   {kw} -> {m.get(kw, '(無)')}")
