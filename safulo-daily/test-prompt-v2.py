#!/usr/bin/env python3
# coding: utf-8
# 讀 sample-result.tsv，挑出問題樣本（含「的」/回無/長輸出），用 v2 prompt 重跑對比
import json, re, urllib.request
from pathlib import Path

OLLAMA_URL = "http://172.18.0.2:11434/api/chat"
MODEL      = "gemma4:26b"
TSV        = Path("sample-result.tsv")


def call_v2(stem, defs_str):
    prompt = (f"阿美語詞條「{stem}」定義：{defs_str}。提取適合搜尋的中文關鍵詞，規則："
              f"(1)每個關鍵詞是單一詞語（2到6字），不要含「的」「地」的短語或變體；"
              f"(2)若詞條本身是地名、部落、山川或人名則保留該名稱，但作為產地、舉例附帶提及的地名人名排除；"
              f"(3)同義詞只留最常用的一個。逗號分隔，無實義則回「無」：")
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

    # 篩問題樣本
    def is_problem(stem, d, r):
        if "的" in r: return True
        if r.strip() in ("無", "「無」", "(無)"): return True
        if len(r) > 40: return True
        if "部落" in d or "村莊" in d or "前綴" in d or "後綴" in d: return True
        return False

    probs = [r for r in rows if is_problem(*r)]
    print(f"問題樣本 {len(probs)} 個，用 v2 prompt 重跑對比：\n")
    for stem, d, old in probs:
        new = call_v2(stem, d)
        print(f"詞條: {stem}")
        print(f"  定義: {d[:50]}")
        print(f"  v1 : {old[:60]}")
        print(f"  v2 : {new[:60]}")
        print()


if __name__ == "__main__":
    main()
