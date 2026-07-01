#!/usr/bin/env python3
# coding: utf-8
import json, random
from pathlib import Path
HERE = Path(__file__).parent
new = json.loads((HERE / "ch-mapping-merged.json").read_text(encoding="utf-8"))
old = json.loads((HERE.parent / "docs" / "s" / "ch-mapping.json").read_text(encoding="utf-8"))
only_old = [k for k in old if k not in new]
only_new = [k for k in new if k not in old]
print("舊有新無:", len(only_old), "  新有舊無:", len(only_new))
random.seed(1)
print("\n舊有新無 抽樣30（看是垃圾還是真詞）:")
print("  " + " | ".join(random.sample(only_old, 30)))
print("\n新有舊無 抽樣20:")
print("  " + " | ".join(random.sample(only_new, 20)))
