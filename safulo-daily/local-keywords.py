# coding: utf-8
# 本機規則式抽詞 v2（取代 smart-chmapping 的「V的N→N」缺陷）
# 修正：殼尾詞（人/器具/樣子…）結尾時，內容在「的」前面，須抽前段動詞片語。
# 用法：python3 local-keywords.py            # 全量重建 → ch-mapping-local.json
#       python3 local-keywords.py --selftest # 只跑樣本驗證
import json, re, sys
from pathlib import Path
import jieba.posseg as pseg

DOCS_S = Path(__file__).parent.parent / 'docs' / 's'

# 泛用/元描述詞：永不當關鍵詞（與 amis_chmapping_llm.py GENERIC 同步）
GENERIC = {
    "東西","對象","地方","事情","物品","事物","情況","方法","行為","方式","情形",
    "一種","疊","後綴","前綴","種類","品種","其他","部分","時間","時候","地點",
    "原因","部位","氣味","樣子","程度","狀態","方面","形狀","用具","器具","處",
    "東西們","名稱","促使","人名","姓氏","短語","短詞","使用","指所","物件","借詞",
    "起來","日語","指被","指要","工具","命令","出來","表示","特地","能夠","準備",
    "做事","閩南語","手段","進去","下來","做成","令人","有意","能力","指有","感到",
    "放在","器物","用來",
}
# 殼尾詞：「<核心>的<殼尾>」時，內容在核心，不是殼尾本身
SHELL_TAILS = {
    "人","者","東西","物","器具","工具","用具","樣子","地方","時間","時候",
    "聲音","動作","狀","物件","對象","人們","傢伙",
}
# 開頭要剝的動作/語法前綴（長到短）
PREFIXES = ["指即將","指將要","指要","指可以","指用來","指","即將","將要",
            "可以","用來","用以","用作","用做","要","也","正在","曾經"]
# 單字內容詞放行：名詞(夢/水/火/刀/魚)+動詞(愛/咬/跑/砍)；不放形容詞(大/小/長/好=噪音)
ALLOW_1CHAR_POS = ("n", "v")
# 單字黑名單（即使 jieba 標成 n/v 也擋）：語法字 + 泛用動詞
STOP_1CHAR = (set("的了是在和與或也都很不沒有指這那個之其所為被把將及等於以由向")
              | set("做弄搞用使讓叫成去來到放給予取得有作"))

def _strip_prefix(t):
    for p in PREFIXES:
        if t.startswith(p):
            return t[len(p):]
    return t

def _seg_content(text):
    """jieba 斷詞，留內容詞（n/v/a），過濾 GENERIC / 單字殼。"""
    out = []
    for w, flag in pseg.cut(text):
        if not re.fullmatch(r"[一-鿿]+", w):
            continue
        if w in GENERIC:
            continue
        if len(w) == 1:
            if flag[0] in ALLOW_1CHAR_POS and w not in STOP_1CHAR:
                out.append(w)
        elif flag[0] in ("n", "v", "a"):
            out.append(w)
    return out

def extract_keywords(definition):
    kws = set()
    text = re.sub(r"[。！？\s]+$", "", definition).strip()
    if not text:
        return []
    # 括號內容單列
    for m in re.findall(r"[（(]([^）)]+)[）)]", text):
        for part in re.split(r"[、，,]", m):
            part = part.strip()
            if part and part not in GENERIC and not re.search(r"[A-Za-z0-9]", part):
                kws.add(part)
    text = re.sub(r"[（(][^）)]*[）)]", "", text).strip()
    # 逗號/頓號/分號切子句
    for part in re.split(r"[，、；,]", text):
        part = _strip_prefix(part.strip())
        if not part:
            continue
        m = re.search(r"^(.*?)的(.+)$", part)
        if m:
            core, tail = m.group(1).strip(), m.group(2).strip()
            if tail in SHELL_TAILS or not tail:
                # 殼尾：內容在 core
                for w in _seg_content(_strip_prefix(core)):
                    kws.add(w)
                continue
            else:
                # 真名詞尾：取 tail（內容名詞），core 的動詞也一併抽
                if tail not in GENERIC and not re.search(r"[A-Za-z0-9]", tail):
                    if len(tail) == 1:
                        for w in _seg_content(tail):
                            kws.add(w)
                    else:
                        kws.add(tail)
                for w in _seg_content(_strip_prefix(core)):
                    kws.add(w)
                continue
        # 無「的」：整句當內容，斷詞抽
        for w in _seg_content(part):
            kws.add(w)
    return [k for k in kws if k and not re.search(r"[A-Za-z0-9]", k)]

SAMPLES = [
    "作夢的人。", "指要摘取的辣椒。", "用來分配獵物的器具。", "生痔瘡的人。",
    "要漂流走，要漂流的東西。", "小米。", "睜大眼睛看著的樣子。",
    "夢、夢占、運氣、夢想。", "稻米。", "野豬。",
]

def main():
    if "--selftest" in sys.argv:
        for s in SAMPLES:
            print(f"{s!r:34} -> {sorted(extract_keywords(s))}")
        return
    xxs = {}
    n = 0
    for fn in sorted(DOCS_S.glob("*.json")):
        try:
            j = json.loads(fn.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(j, dict):
            continue
        stem = j.get("stem") or j.get("t")
        if not stem:
            continue
        n += 1
        for h in j.get("h", []):
            for d in h.get("d", []):
                if "f" in d:
                    for kw in extract_keywords(d["f"]):
                        xxs.setdefault(kw, {}).setdefault(stem, 0)
                        xxs[kw][stem] += 1
    out = {k: ",".join(sorted(v, key=lambda x: -v[x]))
           for k, v in xxs.items() if not re.search(r"[a-z0-9]", k)}
    p = Path(__file__).parent / "ch-mapping-local.json"
    p.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"處理 {n} 詞條，輸出 {len(out)} 關鍵詞 → {p}", file=sys.stderr)

if __name__ == "__main__":
    main()
