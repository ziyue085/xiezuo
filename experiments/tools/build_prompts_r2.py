#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成对照实验的 prompt 文件（第 1/2/3 轮通用）。

A 组与 B 组的任务描述逐字相同，唯一差别是 B 组多一段"按 skill 工作"的说明。

用法：
  python build_prompts_r2.py --round 3
  python build_prompts_r2.py --round 2
  python build_prompts_r2.py --round 1
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SKILL_DIR = ROOT / "literary-craft"

A = "只输出成品正文，不要输出分析过程、不要写标题以外的说明。\n\n"
B = (
    "在动笔之前，先完整阅读 {s}/SKILL.md，按其中第 3 节的路由加载所需的参考文件，"
    "然后按里面的方法完成任务。\n"
    "只输出成品正文，不要输出你的分析过程、不要说明你用了哪些方法。\n\n"
).format(s=str(SKILL_DIR).replace("\\", "/"))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--round", type=int, default=2)
    args = ap.parse_args()
    r = args.round
    scen_dir = SKILL_DIR / "tests" / (f"scenarios-round{r}" if r > 1 else "scenarios")
    out = (ROOT / "experiments" / f"round{r}" / "prompts") if r > 1 else (ROOT / "experiments" / "prompts")
    data = json.loads((scen_dir / "scenarios.json").read_text(encoding="utf-8"))
    out.mkdir(parents=True, exist_ok=True)
    n = 0
    for sc in data["scenarios"]:
        p = sc["prompt"]
        if sc.get("source"):
            p = p.replace("{SOURCE}", (scen_dir / sc["source"]).read_text(encoding="utf-8").strip())
        for arm, prefix in (("A", A), ("B", B)):
            (out / f"{sc['id']}_{arm}.txt").write_text(prefix + p + "\n", encoding="utf-8")
            n += 1
    print(f"{n} files -> {out}")


if __name__ == "__main__":
    main()
