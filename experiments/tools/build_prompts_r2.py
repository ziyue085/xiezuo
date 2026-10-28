#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""第二轮 prompt 生成。A/B 任务描述逐字相同，B 组只多一段 skill 说明。"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SKILL_DIR = ROOT / "literary-craft"
SCEN = SKILL_DIR / "tests" / "scenarios-round2"
OUT = ROOT / "experiments" / "round2" / "prompts"

A = "只输出成品正文，不要输出分析过程、不要写标题以外的说明。\n\n"
B = (
    "在动笔之前，先完整阅读 {s}/SKILL.md，按其中第 3 节的路由加载所需的参考文件，"
    "然后按里面的方法完成任务。\n"
    "只输出成品正文，不要输出你的分析过程、不要说明你用了哪些方法。\n\n"
).format(s=str(SKILL_DIR).replace("\\", "/"))


def main() -> None:
    data = json.loads((SCEN / "scenarios.json").read_text(encoding="utf-8"))
    OUT.mkdir(parents=True, exist_ok=True)
    for sc in data["scenarios"]:
        p = sc["prompt"]
        if sc.get("source"):
            p = p.replace("{SOURCE}", (SCEN / sc["source"]).read_text(encoding="utf-8").strip())
        for arm, prefix in (("A", A), ("B", B)):
            (OUT / f"{sc['id']}_{arm}.txt").write_text(prefix + p + "\n", encoding="utf-8")
    print(f"{len(data['scenarios']) * 2} files -> {OUT}")


if __name__ == "__main__":
    main()
