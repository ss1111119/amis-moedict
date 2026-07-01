#!/usr/bin/env python3
# coding: utf-8
# 修 local bug 後，本機重算 local_kw 並對固定 llm_kw 重跑寬鬆比對。
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

full = partial = conflict = 0
local_extra = llm_extra = 0
for r in rows:
    L, M = r["local_kw"], r["llm_kw"]
    if not L and not M:
        full += 1; continue
    Lc = bool(L) and all(sm(x, M) for x in L)
    Mc = bool(M) and all(sm(y, L) for y in M)
    if Lc and Mc:
        full += 1
    elif any(sm(x, M) for x in L) or any(sm(y, L) for y in M):
        partial += 1
    else:
        conflict += 1
    if Mc and not Lc:
        local_extra += 1
    if Lc and not Mc:
        llm_extra += 1

n = len(rows)
print(f"=== 修 bug 後（本機重算 local，llm 固定）n={n} ===")
print(f"語意完全一致    : {full} ({full/n*100:.1f}%)   [修前 42.5%]")
print(f"部分重疊        : {partial} ({partial/n*100:.1f}%)   [修前 46.9%]")
print(f"真正衝突(零交集): {conflict} ({conflict/n*100:.1f}%)   [修前 10.6%]")
print(f"local多抓(雜訊): {local_extra} [修前59]  |  llm多抓: {llm_extra} [修前8]")
print("\n--- 修過的案例 ---")
for st in ["satefo", "kalafi", "sapitaw", "cifadahan", "tolik", "loham"]:
    r = next((x for x in rows if x["stem"] == st), None)
    if r:
        print(f"  {st}: local={r['local_kw']}  llm={r['llm_kw']}")
