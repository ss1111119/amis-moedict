#!/usr/bin/env python3
# coding: utf-8
# v3 prompt：拆短語 + 嚴格忠於原文、禁止引申腦補。對比 v1（讀 sample-result.tsv）
import json, re, urllib.request
from pathlib import Path

OLLAMA_URL = "http://172.18.0.2:11434/api/chat"
MODEL      = "gemma4:26b"
TSV        = Path("sample-result.tsv")


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


def main():
    rows = []
    for line in TSV.read_text(encoding="utf-8").splitlines():
        parts = line.split("\t")
        if len(parts) == 3:
            rows.append(parts)

    def is_problem(stem, d, r):
        if "的" in r: return True
        if r.strip() in ("無", "「無」", "(無)"): return True
        if len(r) > 40: return True
        if "部落" in d or "村莊" in d or "前綴" in d or "後綴" in d: return True
        return False

    probs = [r for r in rows if is_problem(*r)]
    print(f"問題樣本 {len(probs)} 個，v1 vs v3：\n")
    for stem, d, old in probs:
        new = call_v3(stem, d)
        print(f"詞條: {stem}  | 定義: {d[:46]}")
        print(f"  v1: {old[:60]}")
        print(f"  v3: {new[:60]}")
        print()


if __name__ == "__main__":
    main()
