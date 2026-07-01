#!/usr/bin/env python3
# coding: utf-8
# 策略 C 合併：local_kw + llm_kw 依校準規則合併成 ch-mapping。
#
# 合併規則（每個 stem，清洗後：丟 len<2 / GENERIC / 羅馬字）：
#   1. 有交集      → 取聯集
#   2. 一邊空       → 取非空那邊（空=該法失敗，救回漏抓）
#   3. 地名/部落詞條 → 走 placename-map（通用抽詞不可靠）
#   4. 兩邊非空零交集 → 仍取聯集，但記入 worklist 供選擇性人工複查
#
# 用法：
#   python3 merge-chmapping.py --validate           # 用 probe-compared.json 驗規則
#   python3 merge-chmapping.py local-kw-full.json llm-kw-full.json   # 全量合併
import json, re, sys
from pathlib import Path
import importlib.util

HERE = Path(__file__).parent
DOCS_S = HERE.parent / "docs" / "s"
spec = importlib.util.spec_from_file_location("lk", HERE / "local-keywords.py")
lk = importlib.util.module_from_spec(spec); spec.loader.exec_module(lk)

PLACE_MARK = re.compile(r"部落名稱|社名|地名")
# 結構性單字：保留水/火/夢/愛等內容單字，只擋這些非搜尋詞的單字
JUNK_1CHAR = set("人者物事詞藉處們家名指")

def clean(kws):
    out = []
    for k in kws:
        k = k.strip()
        # 正規化尾字：推走的→推走、來過了→來過、對半分吧→對半分（剝後須 >=2 字）
        while k and k[-1] in "的了吧呢啊" and len(k) - 1 >= 2:
            k = k[:-1]
        if not k or k in lk.GENERIC or re.search(r"[A-Za-z0-9]", k):
            continue
        if len(k) == 1 and (k in JUNK_1CHAR or k in lk.STOP_1CHAR):
            continue  # 擋 人/者/藉 等結構性單字，但保留 水/火/夢/愛
        out.append(k)
    return sorted(set(out))

def dedup_superstring(kws):
    """去除包含另一關鍵詞的冗餘長詞：{推走,推走的}→推走、{編製,魚簍,編製魚簍}→編製,魚簍。"""
    ks = set(kws)
    return sorted(k for k in ks if not any(k != o and o in k for o in ks))

def soft_overlap(L, M):
    return any(a == b or a in b or b in a for a in L for b in M)

def is_placename(defs):
    return any(PLACE_MARK.search(d) or lk._is_admin(d) for d in defs)

def merge_entry(local_kw, llm_kw, defs):
    """回傳 (最終關鍵詞 list, 狀態)。狀態: overlap/recovered/conflict/placename/empty"""
    L, M = clean(local_kw), clean(llm_kw)
    merged = dedup_superstring(set(L) | set(M))
    if is_placename(defs):
        return merged, "placename"
    if not L and not M:
        return [], "empty"
    if not L or not M:
        return merged, "recovered"
    if soft_overlap(L, M):          # 子字串感知，粒度差異不算衝突
        return merged, "overlap"
    return merged, "conflict"


def load_defs(stem):
    """從 docs/s 讀該 stem 的定義（供 placename 判定）。全量合併用。"""
    for name in (stem, "'" + stem):  # 檔名可能帶 apostrophe 前綴
        p = DOCS_S / f"{name}.json"
        if p.exists():
            try:
                j = json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                return []
            return [d.get("f", "") for h in j.get("h", []) for d in h.get("d", []) if d.get("f")]
    return []


def invert_and_write(final, out_path):
    """final: {stem: [kw]} → 反轉 {kw: 'stem1,stem2'}，併 placename-map。
    詞根優先排序：同一中文詞下，關鍵詞數少的 stem（越純粹=越像詞根）排前面。"""
    inv = {}
    for stem, kws in final.items():
        for kw in kws:
            inv.setdefault(kw, []).append(stem)
    out = {k: ",".join(sorted(stems, key=lambda s: (len(final[s]), len(s))))
           for k, stems in inv.items() if not re.search(r"[a-z0-9]", k)}
    # 併入 placename-map（不覆蓋既有詞義）
    pm = HERE.parent / "placename-map.json"
    if pm.exists():
        for k, v in json.loads(pm.read_text(encoding="utf-8")).items():
            out.setdefault(k, v)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    return len(out)


def validate():
    rows = json.loads((HERE / "probe-compared.json").read_text(encoding="utf-8"))
    # 用修好的 local 重算
    from collections import Counter
    stat = Counter()
    worklist = []
    for r in rows:
        lkw = set()
        for d in r["defs"]:
            for w in lk.extract_keywords(d):
                lkw.add(w)
        kws, status = merge_entry(sorted(lkw), r["llm_kw"], r["defs"])
        stat[status] += 1
        if status == "conflict":
            worklist.append((r["stem"], r["defs"], sorted(lkw), r["llm_kw"], kws))
    n = len(rows)
    print(f"=== 合併規則驗證（{n} 筆探針）===")
    for s, c in stat.most_common():
        print(f"  {s:10} {c:4}  {c/n*100:5.1f}%")
    print(f"\n真正需人工(conflict) {len(worklist)} 筆：")
    for stem, defs, L, M, kws in worklist:
        d = "；".join(defs)
        print(f"  [{stem}] {d[:40]}")
        print(f"     local={L}  llm={M}  → 合併={kws}")


def full(local_path, llm_path):
    local = json.loads(Path(local_path).read_text(encoding="utf-8"))
    llm = json.loads(Path(llm_path).read_text(encoding="utf-8"))
    stems = set(local) | set(llm)
    final = {}
    from collections import Counter
    stat = Counter()
    worklist = []
    for stem in stems:
        defs = load_defs(stem)
        kws, status = merge_entry(local.get(stem, []), llm.get(stem, []), defs)
        stat[status] += 1
        if kws:
            final[stem] = kws
        if status == "conflict":
            worklist.append((stem, defs, local.get(stem, []), llm.get(stem, []), kws))
    out_path = HERE / "ch-mapping-merged.json"
    nkeys = invert_and_write(final, out_path)
    wl = HERE / "merge-worklist.tsv"
    with wl.open("w", encoding="utf-8") as f:
        f.write("stem\tdef\tlocal\tllm\tmerged\n")
        for stem, defs, L, M, kws in worklist:
            f.write(f"{stem}\t{'；'.join(defs)}\t{','.join(L)}\t{','.join(M)}\t{','.join(kws)}\n")
    print(f"合併 {len(stems)} 詞條 → {len(final)} 有詞 / {nkeys} 反查 key → {out_path}", file=sys.stderr)
    for s, c in stat.most_common():
        print(f"  {s:10} {c}", file=sys.stderr)
    print(f"人工複查清單 {len(worklist)} 筆 → {wl}", file=sys.stderr)


if __name__ == "__main__":
    if "--validate" in sys.argv:
        validate()
    elif len(sys.argv) >= 3:
        full(sys.argv[1], sys.argv[2])
    else:
        print("用法: merge-chmapping.py --validate | <local-kw-full.json> <llm-kw-full.json>")
