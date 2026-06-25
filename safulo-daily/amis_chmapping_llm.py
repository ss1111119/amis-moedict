#!/usr/bin/env python3
# coding: utf-8
# amis_chmapping_llm.py v2
# 用 Ollama gemma4:26b 重建阿美語中文反查 ch-mapping.json
# 一次處理一個詞條，中斷後重跑從 checkpoint 繼續

import json, re, urllib.request, sys, time
from pathlib import Path

DOCS_S     = Path("docs/s")
CH_MAPPING = DOCS_S / "ch-mapping.json"
CHECKPOINT = Path("amis-chmapping-checkpoint.json")
SKIP       = {"ch-mapping.json", "ch-mapping-smart.json", "ch-mapping-new.json",
              "index.json", "stem-words.json"}
OLLAMA_URL = "http://172.18.0.2:11434/api/generate"
MODEL      = "gemma4:26b"
SAVE_EVERY = 100

GENERIC = {"東西","對象","地方","事情","物品","事物","情況","方法","行為",
           "方式","情形","一種","疊","後綴","前綴","種類","品種","其他","部分"}

SKIP_PREFIXES = ("要","指","〔","即將","將要","把","去","在","也","可以",
                 "讓","用來","使","被","當","請","表示")


def call_ollama(stem, defs):
    defs_str = "；".join(defs[:2])
    prompt = f"阿美語詞條「{stem}」定義：{defs_str}。提取中文搜尋關鍵詞（名詞或形容詞，逗號分隔，無則回「無」）："
    data = json.dumps({
        "model": MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.1, "num_predict": 60}
    }).encode()
    try:
        req = urllib.request.Request(
            OLLAMA_URL, data=data,
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read())
            return result.get("response", "").strip()
    except Exception as e:
        print(f"  [錯誤] {e}", file=sys.stderr)
        return ""


def parse_keywords(response):
    if not response or response.strip() in ("無", "(無)", ""):
        return []
    line = response.split("\n")[0]
    kws = []
    for kw in re.split(r"[,，、/]", line):
        kw = re.sub(r"[。！？\s\d\-\.…—「」【】\[\]〔〕（）()]+", "", kw).strip()
        if (2 <= len(kw) <= 8
                and kw not in GENERIC
                and not re.search(r"[a-zA-Z]", kw)):
            kws.append(kw)
    return kws


def main():
    # 確認 Ollama 連線
    test_url = OLLAMA_URL.replace("/api/generate", "/api/tags")
    try:
        with urllib.request.urlopen(test_url, timeout=5) as r:
            tags = json.loads(r.read())
            names = [m["name"] for m in tags.get("models", [])]
            print(f"Ollama OK，models: {names}", file=sys.stderr)
    except Exception as e:
        print(f"無法連線 Ollama: {e}", file=sys.stderr)
        sys.exit(1)

    # 載入 checkpoint 或從空白開始
    if CHECKPOINT.exists():
        state = json.loads(CHECKPOINT.read_text())
        mapping = state["mapping"]
        processed = set(state["processed"])
        print(f"從 checkpoint 繼續：已處理 {len(processed)} 個，mapping {len(mapping)} 筆",
              file=sys.stderr)
    else:
        mapping = {}
        processed = set()
        print("從零開始重建 ch-mapping", file=sys.stderr)

    files = sorted([f for f in DOCS_S.glob("*.json") if f.name not in SKIP])

    # 篩出有直接定義的詞條
    todo = []
    for fn in files:
        if fn.name in processed:
            continue
        try:
            j = json.loads(fn.read_text())
        except:
            continue
        if not isinstance(j, dict):
            continue
        stem = j.get("t") or j.get("stem", "")
        if not stem:
            continue
        defs = []
        for h in j.get("h", []):
            for d in h.get("d", []):
                f = d.get("f", "")
                if f and not f.startswith(SKIP_PREFIXES):
                    defs.append(f)
        if defs:
            todo.append((fn.name, stem, defs))

    total = len(todo)
    print(f"需處理：{total} 個詞條", file=sys.stderr)

    count = 0
    for i, (fname, stem, defs) in enumerate(todo):
        response = call_ollama(stem, defs)
        keywords = parse_keywords(response)

        for kw in keywords:
            if kw not in mapping:
                mapping[kw] = stem

        # 無論有沒有關鍵詞都標記為已處理
        processed.add(fname)
        count += 1

        if count % SAVE_EVERY == 0:
            CHECKPOINT.write_text(json.dumps(
                {"mapping": mapping, "processed": list(processed)},
                ensure_ascii=False, indent=2
            ))
            pct = (i + 1) / total * 100
            print(f"  [{i+1}/{total}] {pct:.1f}% — {stem}: {keywords} — mapping {len(mapping)} 筆",
                  file=sys.stderr)

    # 最終存檔
    CH_MAPPING.write_text(json.dumps(mapping, ensure_ascii=False, indent=4))
    if CHECKPOINT.exists():
        CHECKPOINT.unlink()
    print(f"完成！ch-mapping.json 共 {len(mapping)} 筆", file=sys.stderr)


if __name__ == "__main__":
    main()
