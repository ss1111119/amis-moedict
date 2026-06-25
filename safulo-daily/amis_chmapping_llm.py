#!/usr/bin/env python3
# coding: utf-8
# amis_chmapping_llm.py
# 用 Ollama gemma3:12b 重建阿美語中文反查 ch-mapping.json
# 用法：python3 amis_chmapping_llm.py
# 中斷後重跑會從 checkpoint 繼續

import json, re, urllib.request, sys, time
from pathlib import Path

DOCS_S      = Path("docs/s")
CH_MAPPING  = DOCS_S / "ch-mapping.json"
CHECKPOINT  = Path("amis-chmapping-checkpoint.json")
SKIP        = {"ch-mapping.json", "ch-mapping-smart.json", "ch-mapping-new.json",
               "index.json", "stem-words.json"}
OLLAMA_URL  = "http://172.18.0.2:11434/api/generate"
MODEL       = "gemma3:12b"
BATCH_SIZE  = 8   # 每次餵幾個詞條給 LLM
SAVE_EVERY  = 200 # 每處理多少個詞存一次 checkpoint

GENERIC = {"東西","對象","地方","事情","物品","事物","情況","方法","行為",
           "方式","情形","一種","疊","後綴","前綴","種類","品種","其他","部分"}

SKIP_PREFIXES = ("要","指","〔","即將","將要","把","去","在","也","可以",
                 "讓","用來","使","被","當","請","表示")


def ollama_ok():
    try:
        urllib.request.urlopen(OLLAMA_URL.replace("/api/generate", "/"), timeout=5)
        return True
    except:
        return False


def call_ollama(batch):
    """batch: list of (stem, [def1, def2, ...])"""
    lines = []
    for stem, defs in batch:
        defs_str = "；".join(defs[:3])
        lines.append(f"詞條「{stem}」：{defs_str}")

    prompt = (
        "你是阿美語字典編輯。以下每行是一個阿美語詞條和它的中文定義。\n"
        "請為每個詞條提取1-4個適合當中文搜尋關鍵詞的名詞或形容詞。\n\n"
        "規則：\n"
        "1. 只取名詞/形容詞，不取動詞框架或句子\n"
        "2. 不取括號舉例（「如房子」「如衣物」這類）\n"
        "3. 不取「把…」「指要…的」「被…了」「表示…」等結構性描述\n"
        "4. 不取泛用詞（東西/對象/地方/方式）\n"
        "5. 若無合適關鍵詞就輸出「(無)」\n\n"
        "輸出格式（每行對應一個詞條，只輸出關鍵詞，逗號分隔）：\n\n"
        + "\n".join(lines)
        + "\n\n請逐行輸出，每行只有關鍵詞："
    )

    data = json.dumps({
        "model": MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.1, "num_predict": 200}
    }).encode()

    try:
        req = urllib.request.Request(
            OLLAMA_URL, data=data,
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read())
            return result.get("response", "").strip()
    except Exception as e:
        print(f"  [錯誤] {e}", file=sys.stderr)
        return ""


def parse_keywords(response, batch):
    output_lines = [l.strip() for l in response.strip().split("\n") if l.strip()]
    results = []
    for i, (stem, _) in enumerate(batch):
        if i >= len(output_lines):
            results.append([])
            continue
        line = output_lines[i]
        if "(無)" in line or line == "無":
            results.append([])
            continue
        kws = []
        for kw in re.split(r"[,，、/]", line):
            kw = re.sub(r"[。！？\s\d\-\.…—]+", "", kw).strip()
            if (2 <= len(kw) <= 8
                    and kw not in GENERIC
                    and not re.search(r"[a-zA-Z\[\]〔〕「」（）…]", kw)):
                kws.append(kw)
        results.append(kws)
    return results


def main():
    # 確認 Ollama 連線
    test_url = OLLAMA_URL.replace("/api/generate", "/api/tags")
    try:
        with urllib.request.urlopen(test_url, timeout=5) as r:
            tags = json.loads(r.read())
            names = [m["name"] for m in tags.get("models", [])]
            print(f"Ollama 連線 OK，可用 models: {names}", file=sys.stderr)
            if MODEL not in names:
                print(f"警告：{MODEL} 不在清單，嘗試繼續...", file=sys.stderr)
    except Exception as e:
        print(f"無法連線 Ollama ({OLLAMA_URL}): {e}", file=sys.stderr)
        sys.exit(1)

    # 載入 checkpoint 或現有 mapping
    if CHECKPOINT.exists():
        state = json.loads(CHECKPOINT.read_text())
        mapping = state["mapping"]
        processed = set(state["processed"])
        print(f"從 checkpoint 繼續：已處理 {len(processed)} 個詞條，mapping {len(mapping)} 筆",
              file=sys.stderr)
    else:
        mapping = json.loads(CH_MAPPING.read_text()) if CH_MAPPING.exists() else {}
        processed = set()
        print(f"從現有 ch-mapping 出發（{len(mapping)} 筆），開始處理...", file=sys.stderr)

    files = sorted([f for f in DOCS_S.glob("*.json") if f.name not in SKIP])
    total = len(files)

    # 篩出有直接定義的詞條（不以動詞前綴開頭）
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

    print(f"需 LLM 處理：{len(todo)}/{total} 個詞條", file=sys.stderr)

    count = 0
    for i in range(0, len(todo), BATCH_SIZE):
        batch_raw = todo[i:i + BATCH_SIZE]
        batch = [(stem, defs) for (_, stem, defs) in batch_raw]

        response = call_ollama(batch)
        if response:
            kw_lists = parse_keywords(response, batch)
            for (fname, stem, _), kws in zip(batch_raw, kw_lists):
                for kw in kws:
                    if kw not in mapping:
                        mapping[kw] = stem
                processed.add(fname)
                count += 1

        if count % SAVE_EVERY == 0 and count > 0:
            CHECKPOINT.write_text(json.dumps(
                {"mapping": mapping, "processed": list(processed)},
                ensure_ascii=False, indent=2
            ))
            done = i + BATCH_SIZE
            pct = done / len(todo) * 100
            print(f"  [{done}/{len(todo)}] {pct:.1f}% — mapping {len(mapping)} 筆",
                  file=sys.stderr)

    # 最終存檔
    CH_MAPPING.write_text(json.dumps(mapping, ensure_ascii=False, indent=4))
    if CHECKPOINT.exists():
        CHECKPOINT.unlink()
    print(f"完成！ch-mapping.json 共 {len(mapping)} 筆關鍵詞", file=sys.stderr)


if __name__ == "__main__":
    main()
