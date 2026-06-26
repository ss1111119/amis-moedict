#!/usr/bin/env python3
# coding: utf-8
# 從地名詞條精煉提取中文地名，建「中文地名 → 阿美羅馬字」對照
import json, re, sys
from pathlib import Path

DOCS_S = Path("docs/s")
SKIP = {"ch-mapping.json", "ch-mapping-smart.json", "ch-mapping-new.json",
        "index.json", "stem-words.json"}

SIG_STRONG = re.compile(r"部落名稱|社名|地名|部落集會所")
SIG_ADMIN  = re.compile(r"[縣市鄉鎮][一-鿿]{0,4}[鄉鎮市區村里]")
SIG_WORD   = re.compile(r"部落|村落|社區")
SIG_TODAY  = re.compile(r"今[台臺]?[灣]?")

# 分層級正則：強制 縣市 → 鄉鎮 → 村/里/部落 順序，吃掉上級避免黏字
LEVEL = re.compile(
    r"(?:[台臺]灣)?"
    r"(?P<county>[一-鿿]{2}[縣市])?"
    r"(?P<town>[一-鿿]{2,3}[鄉鎮區])?"
    r"(?P<vill>[一-鿿]{2,4}(?:村|里|部落|社))"
)
# 開頭舊稱專名：「麻荖漏(部落名稱…」「新港(地名…」
LEAD = re.compile(r"^([一-鿿]{2,5})[（(](?:部落名|地名|地區名)")

TONGMING = ("部落", "村", "里", "社", "鄉", "鎮", "市", "區")


def strip_tongming(name):
    """都蘭村→都蘭、池南部落→池南；長度<2 不留"""
    for t in sorted(TONGMING, key=len, reverse=True):
        if name.endswith(t) and len(name) - len(t) >= 2:
            return name[: -len(t)]
    return None


def main():
    chmap = {}      # 中文地名 → stem
    preview = []
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
        defs = [d.get("f","") for h in j.get("h",[]) for d in h.get("d",[]) if d.get("f","")]
        blob = "；".join(defs)
        if not blob:
            continue
        strong = bool(SIG_STRONG.search(blob))
        admin  = bool(SIG_ADMIN.search(blob))
        if not (strong or (admin and (SIG_TODAY.search(blob) or SIG_WORD.search(blob)))):
            continue

        keys = set()
        # 只看含地名訊號的分句，避免抓到別的義項
        for seg in re.split(r"[；。]", blob):
            if not (SIG_STRONG.search(seg) or SIG_TODAY.search(seg) or SIG_WORD.search(seg)):
                continue
            for m in LEVEL.finditer(seg):
                vill = m.group("vill")
                if vill:
                    keys.add(vill)
                    bare = strip_tongming(vill)
                    if bare:
                        keys.add(bare)
            lead = LEAD.match(seg.strip())
            if lead:
                keys.add(lead.group(1))

        # 後處理1：剝除開頭介詞/修飾詞（之國福里→國福里、原七腳川部落→七腳川部落）
        JUNK = ("之", "的", "場", "附近", "原", "古代", "又指", "指",
                "現今", "今", "阿美族", "地區", "一帶", "古稱")
        cleaned = set()
        for k in keys:
            changed = True
            while changed:
                changed = False
                for p in JUNK:
                    if k.startswith(p) and len(k) - len(p) >= 2:
                        k = k[len(p):]
                        changed = True
            cleaned.add(k)
        keys = cleaned
        # 後處理2：丟掉殘留行政通名（含縣/鄉/鎮/市/區 表示沒切淨）、灣/今、太短
        keys = {k for k in keys
                if len(k) >= 2 and not re.search(r"[縣鄉鎮市區灣今]", k)}
        # 後處理3：黑名單去掉非專名殘渣
        STOP = {"古代", "部落", "阿美族", "村落", "社區", "附近加", "氏族",
                "地區", "一帶", "村莊"}
        keys = {k for k in keys if k not in STOP}
        if not keys:
            continue
        for k in keys:
            chmap.setdefault(k, stem)   # 先到先得
        preview.append((stem, sorted(keys)))

    print(f"地名詞條 {len(preview)} 個，產生中文地名 key {len(chmap)} 筆\n")
    for stem, keys in preview:
        print(f"  {stem:16s} -> {'、'.join(keys)}")

    out = Path("placename-map.json")
    out.write_text(json.dumps(chmap, ensure_ascii=False, indent=2))
    print(f"\n對照表已存 {out}", file=sys.stderr)


if __name__ == "__main__":
    main()
