#!/usr/bin/env python3
# coding: utf-8
# 探針 Stage 1（WSL 跑，需 jieba）：分層抽樣 + 算 local 關鍵詞
# 輸出 probe-sample.json 給伺服器 Stage 2 呼叫 LLM。
# 用法：python3 probe-build-sample.py [每桶K=15]
import json, re, sys, random
from pathlib import Path
import importlib.util

HERE = Path(__file__).parent
DOCS_S = HERE.parent / "docs" / "s"
K = int(sys.argv[1]) if len(sys.argv) > 1 else 15

# 載入 local-keywords 的抽詞器（檔名有連字號，用 spec 載入）
spec = importlib.util.spec_from_file_location("lk", HERE / "local-keywords.py")
lk = importlib.util.module_from_spec(spec); spec.loader.exec_module(lk)

SKIP = {"ch-mapping.json", "ch-mapping-smart.json", "ch-mapping-new.json",
        "ch-mapping-local.json", "index.json", "stem-words.json"}
SKIP_PREFIXES = ("要","指","〔","即將","將要","把","去","在","也","可以",
                 "讓","用來","使","被","當","請","表示")

# 收集母體（與 stratified-sample.py 對齊：同樣的 defs[:2]、同樣 skip 前綴）
items = []
for fn in sorted(DOCS_S.glob("*.json")):
    if fn.name in SKIP:
        continue
    try:
        j = json.loads(fn.read_text(encoding="utf-8"))
    except Exception:
        continue
    if not isinstance(j, dict):
        continue
    stem = j.get("t") or j.get("stem", "")
    if not stem:
        continue
    defs = [d.get("f","") for h in j.get("h",[]) for d in h.get("d",[])
            if d.get("f","") and not d["f"].startswith(SKIP_PREFIXES)]
    if defs:
        items.append((stem, defs[:2]))

features = {
    "含「的」短語":  lambda d: "的" in d,
    "含括號":       lambda d: bool(re.search(r"[（(].*?[）)]", d)),
    "多義項":       lambda d: len(d) >= 2 if isinstance(d, list) else False,
    "含頓號":       lambda d: "、" in d,
    "地名後綴":     lambda d: bool(re.search(r"[縣市鄉鎮村]", d)),
    "部落/社名":    lambda d: ("部落" in d or "社名" in d or "地名" in d),
    "前後綴/短語":  lambda d: bool(re.search(r"前綴|後綴|短語|疊詞|語助", d)),
    "人名/姓氏":    lambda d: bool(re.search(r"人名|姓氏|名字", d)),
    "祈使/命令":    lambda d: bool(re.search(r"促使|命令|祈使", d)),
    "古語字":       lambda d: bool(re.search(r"[臼杵簍寮炊糞汲畚笠廁甕蓑]", d)),
    "超長(>30字)":  lambda d: len(d) > 30,
    "超短(<=4字)":  lambda d: len(d) <= 4,
}

def feat_match(name, pred, defs):
    blob = "；".join(defs)
    if name == "多義項":
        return len(defs) >= 2
    return pred(blob)

random.seed(7)
sample = []
seen = set()
for name, pred in features.items():
    pool = [it for it in items if feat_match(name, pred, it[1])]
    pick = random.sample(pool, min(K, len(pool)))
    for stem, defs in pick:
        if stem in seen:
            continue
        seen.add(stem)
        # local 關鍵詞：對每條 def 抽詞後聯集（與伺服器 LLM 看同樣的 defs）
        lkw = set()
        for d in defs:
            for w in lk.extract_keywords(d):
                lkw.add(w)
        sample.append({
            "stem": stem,
            "bucket": name,
            "defs": defs,
            "local_kw": sorted(lkw),
        })

out = HERE / "probe-sample.json"
out.write_text(json.dumps(sample, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"母體 {len(items)}，抽樣 {len(sample)} 筆（{len(features)} 桶×{K}，去重後）→ {out}",
      file=sys.stderr)
