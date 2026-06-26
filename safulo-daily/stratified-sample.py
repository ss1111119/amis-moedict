#!/usr/bin/env python3
# coding: utf-8
# 分層抽樣：每個句型特徵桶各抽 K 個 + 超長/超短極端值，全部跑 v3，分組檢視
import json, re, urllib.request, sys, random
from pathlib import Path
from collections import defaultdict

DOCS_S = Path("docs/s")
OLLAMA_URL = "http://172.18.0.2:11434/api/chat"
MODEL = "gemma4:26b"
K = int(sys.argv[1]) if len(sys.argv) > 1 else 12
SKIP = {"ch-mapping.json", "ch-mapping-smart.json", "ch-mapping-new.json",
        "index.json", "stem-words.json"}
SKIP_PREFIXES = ("要","指","〔","即將","將要","把","去","在","也","可以",
                 "讓","用來","使","被","當","請","表示")
GENERIC = {"東西","對象","地方","事情","物品","事物","情況","方法","行為","方式",
           "情形","一種","疊","後綴","前綴","種類","品種","其他","部分","時間",
           "時候","地點","原因","部位","氣味","樣子","程度","狀態","方面","形狀",
           "用具","器具","處"}


def call_v3(stem, defs_str):
    prompt = (f"阿美語詞條「{stem}」定義：{defs_str}。從定義中提取適合搜尋的中文關鍵詞。要求："
              f"(1)只取定義中實際出現的詞，嚴禁推測、引申或加入定義沒有的詞；"
              f"(2)關鍵詞用單一詞語，不要含「的」「地」的短語，例如「握手的地方」取「握手」；"
              f"(3)若詞條本身是地名、部落、山川或人名則保留該名稱，但作為產地、出處附帶提及的縣市鄉鎮村要排除。"
              f"逗號分隔，無實義則回「無」：")
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


def parse_filter(resp):
    """模擬主腳本 parse_keywords：過濾泛用詞/英數/長度，顯示最終會入庫的 key"""
    if not resp or resp.strip() in ("無", "「無」", "(無)"):
        return []
    line = resp.split("\n")[0]
    out = []
    for kw in re.split(r"[,，、/]", line):
        kw = re.sub(r"[。！？\s\d\-\.…—「」【】\[\]〔〕（）()]+", "", kw).strip()
        if 2 <= len(kw) <= 8 and kw not in GENERIC and not re.search(r"[a-zA-Z]", kw):
            out.append(kw)
    return out


# 收集
items = []
for fn in sorted(DOCS_S.glob("*.json")):
    if fn.name in SKIP:
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
    defs = [d.get("f","") for h in j.get("h",[]) for d in h.get("d",[])
            if d.get("f","") and not d["f"].startswith(SKIP_PREFIXES)]
    if defs:
        items.append((stem, "；".join(defs[:2])))

features = {
    "含「的」短語":     lambda d: "的" in d,
    "含括號":          lambda d: bool(re.search(r"[（(].*?[）)]", d)),
    "多義項(；)":       lambda d: "；" in d,
    "含頓號":          lambda d: "、" in d,
    "地名後綴":        lambda d: bool(re.search(r"[縣市鄉鎮村]", d)),
    "部落/社名":       lambda d: ("部落" in d or "社名" in d or "地名" in d),
    "前後綴/短語":      lambda d: bool(re.search(r"前綴|後綴|短語|疊詞|語助", d)),
    "省略號…":         lambda d: bool(re.search(r"[…—]|\.\.", d)),
    "人名/姓氏":       lambda d: bool(re.search(r"人名|姓氏|名字", d)),
    "祈使/命令":       lambda d: bool(re.search(r"促使|命令|祈使", d)),
    "超長(>30字)":     lambda d: len(d) > 30,
    "超短(<=4字)":     lambda d: len(d) <= 4,
}

random.seed(7)
seen = set()
print(f"母體 {len(items)}，每桶抽 {K}\n")
for name, pred in features.items():
    pool = [it for it in items if pred(it[1])]
    pick = random.sample(pool, min(K, len(pool)))
    print(f"\n========== {name}（桶 {len(pool)} 個）==========")
    for stem, d in pick:
        resp = call_v3(stem, d)
        kept = parse_filter(resp)
        dup = "  *重複" if stem in seen else ""
        seen.add(stem)
        print(f"  {stem} | {d[:46]}")
        print(f"     v3: {resp[:55]}")
        print(f"     入庫: {kept}{dup}")
