#!/usr/bin/env python3
# coding: utf-8
# 全量 LLM 抽詞（伺服器/ollama）：docs/s 母體 → {stem: [llm_kw]} → llm-kw-full.json
# 每 SAVE_EVERY 存 checkpoint，中斷可續跑（已跑過的 stem 跳過）。
# 複用 amis_chmapping_llm.py 的 call_ollama / parse_keywords，與探針同邏輯。
import json, sys
from pathlib import Path
import importlib.util

HERE = Path(__file__).parent
DOCS_S = HERE.parent / "docs" / "s"
spec = importlib.util.spec_from_file_location("acl", HERE / "amis_chmapping_llm.py")
acl = importlib.util.module_from_spec(spec); spec.loader.exec_module(acl)

OUT = HERE / "llm-kw-full.json"
SAVE_EVERY = 100
SKIP = {"ch-mapping.json", "ch-mapping-smart.json", "ch-mapping-new.json",
        "ch-mapping-local.json", "index.json", "stem-words.json"}
SKIP_PREFIXES = ("要", "指", "〔", "即將", "將要", "把", "去", "在", "也", "可以",
                 "讓", "用來", "使", "被", "當", "請", "表示")

# 續跑：載入已存結果
done = {}
if OUT.exists():
    try:
        done = json.loads(OUT.read_text(encoding="utf-8"))
    except Exception:
        done = {}
print(f"已有 {len(done)} 筆，續跑", file=sys.stderr)

# 母體
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
    stem = j.get("t") or j.get("stem")
    if not stem or stem in done:
        continue
    defs = [d.get("f", "") for h in j.get("h", []) for d in h.get("d", [])
            if d.get("f", "") and not d["f"].startswith(SKIP_PREFIXES)]
    if defs:
        items.append((stem, defs))

print(f"待處理 {len(items)} 筆", file=sys.stderr)
for i, (stem, defs) in enumerate(items, 1):
    resp = acl.call_ollama(stem, defs)
    done[stem] = sorted(set(acl.parse_keywords(resp)))
    if i % SAVE_EVERY == 0:
        OUT.write_text(json.dumps(done, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"  {i}/{len(items)} (存檔)", file=sys.stderr)
OUT.write_text(json.dumps(done, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"完成 {len(done)} 筆 → {OUT}", file=sys.stderr)
