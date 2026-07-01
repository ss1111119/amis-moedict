#!/usr/bin/env python3
# coding: utf-8
# 全量本機抽詞（WSL/jieba）：docs/s 每個詞條 → {stem: [local_kw]} → local-kw-full.json
# 供 merge-chmapping.py 合併用。
import json, sys
from pathlib import Path
import importlib.util

HERE = Path(__file__).parent
DOCS_S = HERE.parent / "docs" / "s"
spec = importlib.util.spec_from_file_location("lk", HERE / "local-keywords.py")
lk = importlib.util.module_from_spec(spec); spec.loader.exec_module(lk)

SKIP = {"ch-mapping.json", "ch-mapping-smart.json", "ch-mapping-new.json",
        "ch-mapping-local.json", "index.json", "stem-words.json"}

out = {}
n = 0
for fn in sorted(DOCS_S.glob("*.json")):
    if fn.name in SKIP:
        continue
    try:
        j = json.loads(fn.read_text(encoding="utf-8"))
    except Exception:
        continue
    if not isinstance(j, dict):
        continue
    stem = j.get("t") or j.get("stem")
    if not stem:
        continue
    kw = set()
    for h in j.get("h", []):
        for d in h.get("d", []):
            if d.get("f"):
                for w in lk.extract_keywords(d["f"]):
                    kw.add(w)
    n += 1
    if kw:
        out[stem] = sorted(kw)
p = HERE / "local-kw-full.json"
p.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"處理 {n} 詞條，{len(out)} 有詞 → {p}", file=sys.stderr)
