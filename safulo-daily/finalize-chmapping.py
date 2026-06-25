#!/usr/bin/env python3
# coding: utf-8
# ch-mapping.json 收尾：短語收斂 + 已知詞條修正
import json, re
from pathlib import Path

P = Path("docs/s/ch-mapping.json")
m = json.load(open(P, encoding="utf-8"))
print(f"收尾前：{len(m)} 筆")

# 1.「X的Y」短語收斂：取「的」後段當 key（隆起的疙瘩 -> 疙瘩）
fixed = {}
samples = []
for k, v in m.items():
    nk = k
    if "的" in k and not k.endswith("的"):
        tail = k.split("的")[-1]
        if 2 <= len(tail) <= 8 and not re.search(r"[a-zA-Z0-9]", tail):
            nk = tail
            if len(samples) < 20:
                samples.append(f"{k} -> {nk}")
    fixed.setdefault(nk, v)  # 先到先得，不覆蓋既有
m = fixed
print(f"短語收斂樣本（前 20）：")
for s in samples:
    print("   ", s)

# 2. 已知詞條修正（強制正確指向）
m["小米"] = "panay"
m["稻米"] = "hafay"
m["稻子"] = "hafay"
m["竹林"] = "'aolan"

json.dump(m, open(P, "w", encoding="utf-8"), ensure_ascii=False, indent=4)
print(f"收尾後：{len(m)} 筆")
for kw in ["小米", "稻米", "稻子", "竹林", "疙瘩"]:
    print(f"   {kw} -> {m.get(kw, '(無)')}")
