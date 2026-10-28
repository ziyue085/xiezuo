#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""由 scenarios.json 生成 A/B 两组的 prompt 文件。

A 组与 B 组的任务描述**逐字相同**，唯一差别是 B 组多一段"按 skill 工作"的说明。
这样可以把差异归因到 skill，而不是 prompt 措辞。
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SKILL_DIR = ROOT / "literary-craft"
SCEN = SKILL_DIR / "tests" / "scenarios"
OUT = ROOT / "experiments" / "prompts"

ARM_A_PREFIX = "只输出成品正文，不要输出分析过程、不要写标题以外的说明。\n\n"
ARM_B_PREFIX = (
    "在动笔之前，先完整阅读 {skill}/SKILL.md，按其中第 3 节的路由加载所需的参考文件，"
    "然后按里面的方法完成任务。\n"
    "只输出成品正文，不要输出你的分析过程、不要说明你用了哪些方法。\n\n"
).format(skill=str(SKILL_DIR).replace("\\", "/"))


def main() -> None:
    data = json.loads((SCEN / "scenarios.json").read_text(encoding="utf-8"))
    OUT.mkdir(parents=True, exist_ok=True)
    for sc in data["scenarios"]:
        prompt = sc["prompt"]
        if sc.get("source"):
            src = (SCEN / sc["source"]).read_text(encoding="utf-8").strip()
            prompt = prompt.replace("{SOURCE}", src)
        for arm, prefix in (("A", ARM_A_PREFIX), ("B", ARM_B_PREFIX)):
            path = OUT / f"{sc['id']}_{arm}.txt"
            path.write_text(prefix + prompt + "\n", encoding="utf-8")
    print(f"written {len(data['scenarios']) * 2} prompt files -> {OUT}")


if __name__ == "__main__":
    main()
