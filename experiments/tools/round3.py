#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""第三轮（v0.1.3 定向验证）流水线：blind / check / aggregate。

与第二轮的区别：
- 硬约束只由脚本判定，评审不打约束分（避免"高分抵消违规"）。
- 评审只评三项：文学效果、语言自然度、事实/内部一致性。
- 每个场景同时输出三级结论：文学效果（相对偏好）、硬约束（通过/违规）、事实准确性（人工核查）。
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import re
import shutil
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
R3 = ROOT / "experiments" / "round3"
SCEN = ROOT / "literary-craft" / "tests" / "scenarios-round3" / "scenarios.json"
sys.path.insert(0, str(ROOT / "literary-craft" / "scripts"))
import craft_lint as cl  # noqa: E402

SEED = 20261028
CJK = re.compile(r"[\u4e00-\u9fff]")
DIMS = ["appeal", "language", "fact"]
CN = {"appeal": "文学效果", "language": "语言自然度", "fact": "事实/内部一致性"}


def scen() -> list[dict]:
    return json.loads(SCEN.read_text(encoding="utf-8"))["scenarios"]


HEDGES = ("通行说法", "所谓", "并非", "不是", "错", "至少早了", "这句话", "把诏书", "一半是真的")


def asserts(text: str, phrase: str, window: int = 24) -> bool:
    """禁用词是否被"主张"而非"引用后否定"。附近有否定/引述词就不算主张。"""
    start = 0
    while True:
        i = text.find(phrase, start)
        if i < 0:
            return False
        near = text[max(0, i - window): i + len(phrase) + window]
        if not any(h in near for h in HEDGES):
            return True
        start = i + len(phrase)


def chars(t: str) -> int:
    return len(CJK.findall(t))


def cmd_blind(_a) -> None:
    rng = random.Random(SEED)
    keys = {"blind": {}, "blind2": {}}
    for sc in scen():
        sid = sc["id"]
        arms = ["A", "B"]
        rng.shuffle(arms)
        labels = dict(zip(["甲", "乙"], arms))
        keys["blind"][sid] = labels
        keys["blind2"][sid] = {"甲": labels["乙"], "乙": labels["甲"]}
        for base in ("blind", "blind2"):
            d = R3 / base / sid
            d.mkdir(parents=True, exist_ok=True)
            task = sc["prompt"].split("\n\n---\n")[0]
            (d / "task.txt").write_text(
                f"【体裁】{sc['mode']}\n【字数区间】{sc['words'][0]}-{sc['words'][1]} 字\n"
                f"【任务】\n{task}\n", encoding="utf-8")
            for label, arm in keys[base][sid].items():
                shutil.copyfile(R3 / "runs" / sid / f"{arm}.md", d / f"{label}.txt")
    for base in ("blind", "blind2"):
        (R3 / base / "key.json").write_text(
            json.dumps(keys[base], ensure_ascii=False, indent=2), encoding="utf-8")
        print(base, json.dumps(keys[base], ensure_ascii=False))


def cmd_check(_a) -> None:
    rows = []
    for sc in scen():
        for arm in ("A", "B"):
            p = R3 / "runs" / sc["id"] / f"{arm}.md"
            if not p.exists():
                continue
            text = p.read_text(encoding="utf-8")
            n = chars(text)
            lo, hi = sc["words"]
            r = {"sid": sc["id"], "arm": arm, "chars": n,
                 "range": f"{lo}-{hi}", "length_ok": lo <= n <= hi}
            ck = sc.get("checks", {})
            if "min_chars" in ck:
                r["min_ok"] = n >= ck["min_chars"]
            if "max_chars" in ck:
                r["max_ok"] = n <= ck["max_chars"]
            if "must_keep" in ck:
                miss = [k for k in ck["must_keep"]
                        if not any(x and x in text for x in k.split("|"))]
                r["must_keep"] = f"{len(ck['must_keep']) - len(miss)}/{len(ck['must_keep'])}"
                r["missing"] = ",".join(miss)
            if "must_not" in ck:
                bad = [k for k in ck["must_not"] if asserts(text, k)]
                r["must_not"] = f"{len(bad)}/{len(ck['must_not'])}"
                r["bad"] = ",".join(bad)
            if "min_numbers" in ck:
                r["numbers"] = len(re.findall(r"\d+(?:\.\d+)?", text))
            # 硬约束：任一项不过即违规
            hard = []
            if not r["length_ok"]:
                hard.append("LENGTH")
            if r.get("missing"):
                hard.append("FACT_LOSS")
            if r.get("bad"):
                hard.append("FORBIDDEN")
            r["hard_fail"] = "|".join(hard)
            r["hard_pass"] = not hard
            rows.append(r)
    keys = list(dict.fromkeys(k for r in rows for k in r))
    with (R3 / "checks.csv").open("w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=keys)
        w.writeheader(); w.writerows(rows)
    head = "| 场景 | 组 | 字数 | 区间 | 篇幅 | 必留项 | 缺 | 禁用词 | 硬约束 |"
    sep = "|---|---|---|---|---|---|---|---|---|"
    lines = [head, sep]
    for r in rows:
        lines.append(f"| {r['sid']} | {r['arm']} | {r['chars']} | {r['range']} | "
                     f"{'✓' if r['length_ok'] else '✗'} | {r.get('must_keep','-')} | "
                     f"{r.get('missing','')} | {r.get('must_not','-')} | "
                     f"{'通过' if r['hard_pass'] else r['hard_fail']} |")
    (R3 / "checks.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


def load(p: Path) -> list[dict]:
    if not p.exists():
        return []
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]


def cmd_aggregate(_a) -> None:
    keys = {b: json.loads((R3 / b / "key.json").read_text(encoding="utf-8"))
            for b in ("blind", "blind2")}
    judges = [("j1", "judge1.jsonl", "blind"), ("j2", "judge2.jsonl", "blind2")]
    data = {n: ({r["sid"]: r for r in load(R3 / "judgments" / f)}, keys[k])
            for n, f, k in judges}
    overall = Counter()
    dim = {d: Counter() for d in DIMS}
    per = {}
    for sc in scen():
        sid = sc["id"]; per[sid] = {}
        for n, (rows, k) in data.items():
            r = rows.get(sid)
            if not r:
                per[sid][n] = "NA"; continue
            dec = k[sid].get(r["overall"], "TIE")
            per[sid][n] = dec
            overall[dec] += 1
            for d in DIMS:
                dim[d][k[sid].get(r["dims"].get(d, "平"), "TIE")] += 1
    lines = ["# 第三轮盲评（文学效果，硬约束不计入）", "",
             "| 场景 | j1 | j2(换位) |", "|---|---|---|"]
    for sc in scen():
        v = per[sc["id"]]
        lines.append(f"| {sc['id']} {sc['title']} | {v.get('j1')} | {v.get('j2')} |")
    b, a, t = overall["B"], overall["A"], overall["TIE"]
    lines += ["", f"**总计：B {b} / A {a} / 平 {t}**", "",
              "| 维度 | B | A | 平 |", "|---|---|---|---|"]
    for d in DIMS:
        c = dim[d]
        lines.append(f"| {CN[d]} | {c['B']} | {c['A']} | {c['TIE']} |")
    (R3 / "judgments" / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["blind", "check", "aggregate"])
    args = ap.parse_args()
    {"blind": cmd_blind, "check": cmd_check, "aggregate": cmd_aggregate}[args.cmd](args)


if __name__ == "__main__":
    main()
