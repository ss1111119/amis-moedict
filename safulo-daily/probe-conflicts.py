#!/usr/bin/env python3
# coding: utf-8
# 列出修 local 後仍真正衝突（零交集）的案例，供人工校準「衝突時取誰」。
import json, importlib.util
from pathlib import Path
HERE = Path(__file__).parent
spec = importlib.util.spec_from_file_location("lk", HERE / "local-keywords.py")
lk = importlib.util.module_from_spec(spec); spec.loader.exec_module(lk)
rows = json.loads((HERE / "probe-compared.json").read_text(encoding="utf-8"))
for r in rows:
    s = set()
    for d in r["defs"]:
        for w in lk.extract_keywords(d):
            s.add(w)
    r["local_kw"] = sorted(s)

def sm(a, b):
    return any(a == y or a in y or y in a for y in b) if b else False

i = 0
for r in rows:
    L, M = r["local_kw"], r["llm_kw"]
    if not L and not M:
        continue
    if any(sm(x, M) for x in L) or any(sm(y, L) for y in M):
        continue
    i += 1
    d = "；".join(r["defs"])
    d = d[:44] + "…" if len(d) > 44 else d
    print(f"{i:2} [{r['bucket']}] {r['stem']}")
    print(f"     定義: {d}")
    print(f"     local={L}")
    print(f"     llm  ={M}")
