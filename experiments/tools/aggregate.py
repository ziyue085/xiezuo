#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""汇总盲评：把"甲/乙"解码成 A/B，算胜率、一致性与位置偏差检验。

judge1 / judge2 使用同一套标签；judge3 使用**标签互换**的第二套材料
（blind2），用于检验是否存在"甲位偏好"。如果换位后结论不变，
说明结果不是由位置造成的。
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EXP = ROOT / "experiments"
JDIR = EXP / "judgments"

DIMS = ["continue", "character", "scene", "plot", "emotion", "language", "padding", "compliance"]
CN = {
    "continue": "继续阅读意愿", "character": "人物鲜活度", "scene": "场景可感度",
    "plot": "情节推进自然度", "emotion": "情绪感染力", "language": "语言自然度",
    "padding": "堆砌与注水（少者胜）", "compliance": "题材与约束契合",
}
JUDGES = [("judge1", "judge1.jsonl", "blind"),
          ("judge2", "judge2.jsonl", "blind"),
          ("judge3", "judge3.jsonl", "blind2"),
          ("judge4", "judge4.jsonl", "blind2")]


def load(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def decode(label: str, key: dict) -> str:
    return key.get(label, "TIE") if label in ("甲", "乙") else "TIE"


def main() -> None:
    keys = {d: json.loads((EXP / d / "key.json").read_text(encoding="utf-8")) for d in ("blind", "blind2")}
    data = {}
    for name, fname, kd in JUDGES:
        rows = {r["sid"]: r for r in load(JDIR / fname)}
        data[name] = (rows, keys[kd])

    sids = sorted(keys["blind"])
    overall = Counter()
    per_scene = {}
    dim_stat = {d: Counter() for d in DIMS}
    agree_pairs = 0
    agree_same = 0

    for sid in sids:
        per_scene[sid] = {}
        picks = {}
        for name, (rows, key) in data.items():
            r = rows.get(sid)
            if not r:
                per_scene[sid][name] = "NA"
                continue
            dec = decode(r["overall"], key[sid])
            per_scene[sid][name] = dec
            overall[dec] += 1
            picks[name] = {d: decode(r["dims"].get(d, "平"), key[sid]) for d in DIMS}
            for d in DIMS:
                dim_stat[d][picks[name][d]] += 1
        # 成对一致性
        names = list(picks)
        for i in range(len(names)):
            for j in range(i + 1, len(names)):
                for d in DIMS:
                    agree_pairs += 1
                    if picks[names[i]][d] == picks[names[j]][d]:
                        agree_same += 1

    lines = ["# 盲评汇总", "",
             "A = 直接写作；B = 启用 skill。judge3 使用**标签互换**的一套材料，用于检验位置偏差。", "",
             "## 逐场景总评", "",
             "| 场景 | judge1 | judge2 | judge3(换位·苛刻) | judge4(换位·中性) | 票数 |", "|---|---|---|---|---|---|"]
    stable = []
    for sid in sids:
        r = per_scene[sid]
        votes = [r.get(k, "NA") for k in ("judge1", "judge2", "judge3", "judge4")]
        nb = votes.count("B"); na = votes.count("A")
        tag = "B 稳定" if nb >= 3 else ("A 稳定" if na >= 3 else "分歧")
        if nb >= 3 or na >= 3:
            stable.append(sid)
        lines.append(f"| {sid} | {votes[0]} | {votes[1]} | {votes[2]} | {votes[3]} | B{ nb }-A{ na }（{tag}） |")

    b, a, t = overall["B"], overall["A"], overall["TIE"]
    lines += ["", f"**总评：B 胜 {b}，A 胜 {a}，平 {t}**（{b + a + t} 次判断）", "",
              "## 分维度", "",
              "| 维度 | B 胜 | A 胜 | 平 | B 胜率(去平) |", "|---|---|---|---|---|"]
    for d in DIMS:
        c = dim_stat[d]
        rate = f"{c['B'] / (c['B'] + c['A']):.0%}" if (c["B"] + c["A"]) else "-"
        lines.append(f"| {CN[d]} | {c['B']} | {c['A']} | {c['TIE']} | {rate} |")
    lines += ["", f"三-四维度成对一致率：{agree_same}/{agree_pairs} = {agree_same / agree_pairs:.1%}",
              f"方向稳定（≥3/4 评审同向）的场景：{len(stable)}/10 —— {', '.join(stable)}"]

    # 位置偏差：judge1/2 在 blind 上，judge3 在 blind2 上；比较各评审的 A/B 选择是否稳定
    summary = {
        "overall": dict(overall),
        "dims": {d: dict(dim_stat[d]) for d in DIMS},
        "per_scene": per_scene,
        "pairwise_agreement": f"{agree_same}/{agree_pairs}",
    }
    (JDIR / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    (JDIR / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
