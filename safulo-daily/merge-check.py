#!/usr/bin/env python3
# coding: utf-8
import json
from pathlib import Path
HERE = Path(__file__).parent
new = json.loads((HERE / "ch-mapping-merged.json").read_text(encoding="utf-8"))
old = json.loads((HERE.parent / "docs" / "s" / "ch-mapping.json").read_text(encoding="utf-8"))
print("舊 ch-mapping key 數:", len(old))
print("新 merged   key 數:", len(new))
print()
for w in ["小米", "稻米", "夢", "水", "火", "豬", "筷子", "痔瘡", "斗笠",
          "眼睛", "愛", "部落", "都蘭", "麒麟"]:
    v = [x for x in new.get(w, "").split(",") if x]
    print(f"  {w:<4} ({len(v):2}): {','.join(v[:8])}")
print("\n--- worklist 前 15 筆 ---")
for line in (HERE / "merge-worklist.tsv").read_text(encoding="utf-8").splitlines()[1:16]:
    c = line.split("\t")
    if len(c) >= 5:
        print(f"  {c[0]}: {c[1][:32]} | local={c[2]} llm={c[3]}")
