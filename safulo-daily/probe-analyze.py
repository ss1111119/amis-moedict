#!/usr/bin/env python3
# coding: utf-8
# 探針 Stage 3：比對 local vs LLM，算一致率、分類、列不一致工單。
# 用法：python3 probe-analyze.py
import json
from pathlib import Path
from collections import Counter, defaultdict

HERE = Path(__file__).parent
rows = json.loads((HERE / "probe-compared.json").read_text(encoding="utf-8"))

def classify(L, M):
    L, M = set(L), set(M)
    if not L and not M: return "BOTH_EMPTY"
    if not M:           return "LLM_EMPTY"      # local 有、LLM 無
    if not L:           return "LOCAL_EMPTY"    # LLM 有、local 無
    if L == M:          return "SAME"
    if L <= M:          return "LLM_SUPERSET"   # 方向一致，LLM 多抓
    if M <= L:          return "LOCAL_SUPERSET" # 方向一致，local 多抓
    if L & M:           return "OVERLAP"        # 部分交集
    return "DISJOINT"                            # 完全不一致（最該看）

def jaccard(L, M):
    L, M = set(L), set(M)
    if not L and not M: return 1.0
    return len(L & M) / len(L | M) if (L | M) else 1.0

cls = Counter()
buck = defaultdict(Counter)
jsum = 0.0
worklist = []
for r in rows:
    c = classify(r["local_kw"], r["llm_kw"])
    cls[c] += 1
    buck[r["bucket"]][c] += 1
    jsum += jaccard(r["local_kw"], r["llm_kw"])
    if c in ("DISJOINT", "OVERLAP", "LLM_EMPTY", "LOCAL_EMPTY"):
        worklist.append((c, r))

n = len(rows)
agree = cls["SAME"] + cls["LLM_SUPERSET"] + cls["LOCAL_SUPERSET"] + cls["BOTH_EMPTY"]
print(f"=== 樣本 {n} 筆 ===")
print(f"平均 Jaccard: {jsum/n:.3f}")
print(f"方向一致(SAME/SUPERSET/BOTH_EMPTY): {agree} ({agree/n*100:.1f}%)")
print(f"需人工看(DISJOINT/OVERLAP/單邊空): {n-agree} ({(n-agree)/n*100:.1f}%)")
print("\n--- 分類分布 ---")
for c, k in cls.most_common():
    print(f"  {c:14} {k:4}  {k/n*100:5.1f}%")

print("\n--- 各桶 需人工看比例 ---")
for b, cc in buck.items():
    tot = sum(cc.values())
    bad = cc["DISJOINT"]+cc["OVERLAP"]+cc["LLM_EMPTY"]+cc["LOCAL_EMPTY"]
    print(f"  {b:14} {bad}/{tot}")

# 輸出工單 TSV
wl = HERE / "probe-worklist.tsv"
with wl.open("w", encoding="utf-8") as f:
    f.write("class\tstem\tbucket\tdef\tlocal_kw\tllm_kw\n")
    for c, r in sorted(worklist, key=lambda x: x[0]):
        f.write(f"{c}\t{r['stem']}\t{r['bucket']}\t{'；'.join(r['defs'])}\t"
                f"{','.join(r['local_kw'])}\t{','.join(r['llm_kw'])}\n")
print(f"\n不一致工單 {len(worklist)} 筆 → {wl}")
print("\n--- DISJOINT 樣例（最該人工看）---")
for c, r in worklist:
    if c == "DISJOINT":
        print(f"  {r['stem']} | {'；'.join(r['defs'])[:40]}")
        print(f"     local={r['local_kw']}  llm={r['llm_kw']}")
