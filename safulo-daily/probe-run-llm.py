#!/usr/bin/env python3
# coding: utf-8
# 探針 Stage 2（伺服器跑，連得到 ollama，不需 jieba）：
# 讀 probe-sample.json，對每筆呼叫 LLM，附 llm_kw，輸出 probe-compared.json。
# 複用 amis_chmapping_llm.py 的 call_ollama / parse_keywords，與正式管線同邏輯。
import json, sys
from pathlib import Path
import importlib.util

HERE = Path(__file__).parent
spec = importlib.util.spec_from_file_location("acl", HERE / "amis_chmapping_llm.py")
acl = importlib.util.module_from_spec(spec); spec.loader.exec_module(acl)

sample = json.loads((HERE / "probe-sample.json").read_text(encoding="utf-8"))
out = []
for i, row in enumerate(sample, 1):
    resp = acl.call_ollama(row["stem"], row["defs"])
    row["llm_raw"] = resp
    row["llm_kw"] = sorted(set(acl.parse_keywords(resp)))
    out.append(row)
    if i % 20 == 0:
        print(f"  {i}/{len(sample)}", file=sys.stderr)

p = HERE / "probe-compared.json"
p.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"完成 {len(out)} 筆 → {p}", file=sys.stderr)
