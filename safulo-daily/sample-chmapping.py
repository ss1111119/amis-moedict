#!/usr/bin/env python3
# coding: utf-8
# 抽樣分析：隨機抽 N 個詞條跑 LLM，觀察定義多樣性與 LLM 輸出問題模式
import json, re, urllib.request, sys, random
from pathlib import Path

DOCS_S     = Path("docs/s")
OLLAMA_URL = "http://172.18.0.2:11434/api/chat"
MODEL      = "gemma4:26b"
N          = int(sys.argv[1]) if len(sys.argv) > 1 else 400
OUT_TSV    = Path("sample-result.tsv")

SKIP = {"ch-mapping.json", "ch-mapping-smart.json", "ch-mapping-new.json",
        "index.json", "stem-words.json"}
SKIP_PREFIXES = ("要","指","〔","即將","將要","把","去","在","也","可以",
                 "讓","用來","使","被","當","請","表示")
GENERIC = {"東西","對象","地方","事情","物品","事物","情況","方法","行為",
           "方式","情形","一種","疊","後綴","前綴","種類","品種","其他","部分",
           "氣味","部位","時候","樣子","程度","狀態","動作","方面"}


def call_ollama(stem, defs):
    defs_str = "；".join(defs[:2])
    prompt = (f"阿美語詞條「{stem}」定義：{defs_str}。提取適合當搜尋的中文關鍵詞。"
              f"若詞條本身就是某地名、部落、山川或人名，保留該名稱；"
              f"但作為產地、出處、舉例而附帶提及的地名人名要排除。逗號分隔，無則回「無」：")
    data = json.dumps({"model": MODEL, "messages": [{"role": "user", "content": prompt}],
                       "stream": False, "think": False,
                       "options": {"temperature": 0.1, "num_predict": 60}}).encode()
    try:
        req = urllib.request.Request(OLLAMA_URL, data=data,
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read()).get("message", {}).get("content", "").strip()
    except Exception as e:
        return f"[錯誤]{e}"


def main():
    files = sorted([f for f in DOCS_S.glob("*.json") if f.name not in SKIP])
    todo = []
    for fn in files:
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
            todo.append((stem, defs))

    random.seed(42)
    sample = random.sample(todo, min(N, len(todo)))
    print(f"母體 {len(todo)} 個詞條，抽樣 {len(sample)} 個", file=sys.stderr)

    rows = []
    for i, (stem, defs) in enumerate(sample):
        resp = call_ollama(stem, defs)
        rows.append((stem, "；".join(defs[:2]), resp))
        if (i + 1) % 50 == 0:
            print(f"  {i+1}/{len(sample)}", file=sys.stderr)

    # 存完整結果
    with open(OUT_TSV, "w", encoding="utf-8") as f:
        for stem, d, resp in rows:
            f.write(f"{stem}\t{d}\t{resp}\n")

    # 分類統計
    n = len(rows)
    n_none   = sum(1 for _,_,r in rows if r.strip() in ("無","「無」","(無)"))
    n_err    = sum(1 for _,_,r in rows if r.startswith("[錯誤]"))
    n_de     = sum(1 for _,_,r in rows if "的" in r)
    n_generic= sum(1 for _,_,r in rows if any(g in re.split(r"[,，、]", r) for g in GENERIC))
    n_punct  = sum(1 for _,_,r in rows if re.search(r"[（(）)。]", r))
    n_long   = sum(1 for _,_,r in rows if any(len(k.strip())>6 for k in re.split(r"[,，、]", r)))

    print("\n===== 統計 =====")
    print(f"總數              {n}")
    print(f"回「無」           {n_none}  ({n_none/n*100:.1f}%)")
    print(f"錯誤              {n_err}")
    print(f"含「的」短語        {n_de}  ({n_de/n*100:.1f}%)")
    print(f"含泛用詞          {n_generic}  ({n_generic/n*100:.1f}%)")
    print(f"含標點(括號句號)   {n_punct}  ({n_punct/n*100:.1f}%)")
    print(f"含>6字長詞        {n_long}  ({n_long/n*100:.1f}%)")

    def show(title, pred, limit=15):
        hits = [(s,d,r) for s,d,r in rows if pred(s,d,r)]
        print(f"\n===== {title}（{len(hits)} 個，列前 {min(limit,len(hits))}）=====")
        for s,d,r in hits[:limit]:
            print(f"  {s} | {d[:30]} | => {r}")

    show("含「的」短語", lambda s,d,r: "的" in r)
    show("含泛用詞", lambda s,d,r: any(g in re.split(r"[,，、]", r) for g in GENERIC))
    show("回「無」", lambda s,d,r: r.strip() in ("無","「無」","(無)"))
    show("含標點", lambda s,d,r: re.search(r"[（(）)。]", r))
    print(f"\n完整結果已存 {OUT_TSV}", file=sys.stderr)


if __name__ == "__main__":
    main()
