#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 A/B 成品复制成匿名对照，随机分配"甲/乙"标签。

盲评前提：评审者不知道哪一份来自 skill。
随机种子固定，保证可复现；密钥单独存放在 key.json，评审时不给评审者看。
"""

from __future__ import annotations

import json
import random
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUNS = ROOT / "experiments" / "runs"
BLIND = ROOT / "experiments" / "blind"
SCEN = ROOT / "literary-craft" / "tests" / "scenarios" / "scenarios.json"
SEED = 20261028


def main() -> None:
    data = json.loads(SCEN.read_text(encoding="utf-8"))
    rng = random.Random(SEED)
    BLIND.mkdir(parents=True, exist_ok=True)
    key = {}
    for sc in data["scenarios"]:
        sid = sc["id"]
        d = BLIND / sid
        d.mkdir(parents=True, exist_ok=True)
        arms = ["A", "B"]
        rng.shuffle(arms)
        labels = dict(zip(["甲", "乙"], arms))
        for label, arm in labels.items():
            src = RUNS / sid / f"{arm}.md"
            shutil.copyfile(src, d / f"{label}.txt")
        # 任务说明（评审者可见，用于判断是否切题）
        task = sc["prompt"].split("\n\n---\n")[0]
        (d / "task.txt").write_text(
            f"【体裁】{sc['mode']}\n【任务】\n{task}\n", encoding="utf-8"
        )
        key[sid] = labels
    (BLIND / "key.json").write_text(
        json.dumps(key, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(key, ensure_ascii=False))


if __name__ == "__main__":
    main()
