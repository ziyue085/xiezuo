#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""第二轮实验的流水线：blind / analyze / aggregate。

用法：
  python round2.py blind       # 生成匿名对照（blind + 标签互换的 blind2）
  python round2.py analyze     # 客观指标 + 硬约束检查
  python round2.py aggregate   # 汇总盲评

第二轮与第一轮完全隔离：目录、场景、评审文件都不共用。
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import re
import shutil
import statistics as st
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
R2 = ROOT / "experiments" / "round2"
SCEN = ROOT / "literary-craft" / "tests" / "scenarios-round2" / "scenarios.json"
sys.path.insert(0, str(ROOT / "literary-craft" / "scripts"))
import craft_lint as cl  # noqa: E402

SEED = 20261028
CJK = re.compile(r"[\u4e00-\u9fff]")
NUM = re.compile(r"\d+(?:\.\d+)?")
CN_NUM = re.compile(
    r"[一二三四五六七八九十百千万亿零两半]+"
    r"(?:块|元|毛|角|斤|两|个|张|袋|桶|碗|文|贯|石|斗|亩|人|户|里|年|天|日|月|分|钱|口|余)"
)
DIMS = ["appeal", "language", "consistency", "compliance"]
CN = {"appeal": "阅读吸引力", "language": "语言自然度",
      "consistency": "人物与事实一致性", "compliance": "约束遵守"}


def scenarios() -> list[dict]:
    return json.loads(SCEN.read_text(encoding="utf-8"))["scenarios"]


def chars(t: str) -> int:
    return len(CJK.findall(t))


# ---------------------------------------------------------------- blind
def cmd_blind(_args) -> None:
    rng = random.Random(SEED)
    keys = {"blind": {}, "blind2": {}}
    for sc in scenarios():
        sid = sc["id"]
        arms = ["A", "B"]
        rng.shuffle(arms)
        labels = dict(zip(["甲", "乙"], arms))
        keys["blind"][sid] = labels
        keys["blind2"][sid] = {"甲": labels["乙"], "乙": labels["甲"]}
        for base in ("blind", "blind2"):
            d = R2 / base / sid
            d.mkdir(parents=True, exist_ok=True)
            task = sc["prompt"].split("\n\n---\n")[0]
            (d / "task.txt").write_text(
                f"【体裁】{sc['mode']}\n【字数区间】{sc['words'][0]}-{sc['words'][1]} 字\n"
                f"【任务】\n{task}\n", encoding="utf-8")
        for base in ("blind", "blind2"):
            for label, arm in keys[base][sid].items():
                shutil.copyfile(R2 / "runs" / sid / f"{arm}.md", R2 / base / sid / f"{label}.txt")
    for base in ("blind", "blind2"):
        (R2 / base / "key.json").write_text(
            json.dumps(keys[base], ensure_ascii=False, indent=2), encoding="utf-8")
        print(base, json.dumps(keys[base], ensure_ascii=False))


# ---------------------------------------------------------------- analyze
def cmd_analyze(_args) -> None:
    rows, checks = [], []
    for sc in scenarios():
        for arm in ("A", "B"):
            p = R2 / "runs" / sc["id"] / f"{arm}.md"
            if not p.exists():
                continue
            text = p.read_text(encoding="utf-8")
            res = cl.analyze(text, mode=sc["mode"],
                             era="ancient" if sc["mode"] == "history" else "")
            m = res["metrics"]
            rows.append({"sid": sc["id"], "mode": sc["mode"], "arm": arm,
                         "char": m["chars"], "sent_cv": m["sent_cv"],
                         "short_pct": m["short_pct"], "dialogue_pct": m["dialogue_pct"],
                         "emotion_per_k": m["emotion_naming_per_k"],
                         "cliche_per_k": m["cliche_per_k"],
                         "abstract_per_k": m["abstract_per_k"],
                         "flags": len(res["flags"]),
                         "flag_codes": "|".join(f["code"] for f in res["flags"])})
            c = {"sid": sc["id"], "arm": arm, "chars": m["chars"],
                 "words_lo": sc["words"][0], "words_hi": sc["words"][1]}
            c["length_ok"] = sc["words"][0] <= m["chars"] <= sc["words"][1]
            ck = sc.get("checks", {})
            if "min_chars" in ck:
                c["min_chars_ok"] = m["chars"] >= ck["min_chars"]
            if "max_chars" in ck:
                c["max_chars_ok"] = m["chars"] <= ck["max_chars"]
            if "must_keep" in ck:
                kept = [k for k in ck["must_keep"] if any(x and x in text for x in k.split("|"))]
                c["must_keep"] = f"{len(kept)}/{len(ck['must_keep'])}"
                c["missing"] = ",".join(k for k in ck["must_keep"]
                                        if not any(x and x in text for x in k.split("|")))
            if "must_not" in ck:
                body = re.split(r"\n\s*(?:改动说明|史实与虚构|说明)", text)[0]
                bad = [k for k in ck["must_not"] if k in body]
                c["must_not_hit"] = f"{len(bad)}/{len(ck['must_not'])}"
                c["bad_words"] = ",".join(bad)
            if "min_numbers" in ck:
                n = len(NUM.findall(text)) + len(CN_NUM.findall(text))
                c["numbers"] = n
                c["min_numbers_ok"] = n >= ck["min_numbers"]
            checks.append(c)

    with (R2 / "metrics.csv").open("w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader(); w.writerows(rows)
    with (R2 / "checks.csv").open("w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=sorted({k for c in checks for k in c}))
        w.writeheader(); w.writerows(checks)

    lines = ["| 场景 | 组 | 字数 | 区间 | 合规 | 句长CV | 对话% | 情绪命名/千 | 提示数 |",
             "|---|---|---|---|---|---|---|---|---|"]
    for c in checks:
        r = next(x for x in rows if x["sid"] == c["sid"] and x["arm"] == c["arm"])
        lines.append(f"| {c['sid']} | {c['arm']} | {c['chars']} | {c['words_lo']}-{c['words_hi']} | "
                     f"{'✓' if c['length_ok'] else '✗'} | {r['sent_cv']} | {r['dialogue_pct']} | "
                     f"{r['emotion_per_k']} | {r['flags']} |")
    (R2 / "metrics.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    ok = sum(1 for c in checks if c["length_ok"])
    print(f"\n篇幅合规 {ok}/{len(checks)}")


# ---------------------------------------------------------------- aggregate
def load(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def cmd_aggregate(_args) -> None:
    keys = {b: json.loads((R2 / b / "key.json").read_text(encoding="utf-8"))
            for b in ("blind", "blind2")}
    judges = [("judgeR1", "judgeR1.jsonl", "blind"),
              ("judgeR2", "judgeR2.jsonl", "blind2"),
              ("judgeR3", "judgeR3.jsonl", "blind2")]
    data = {n: ({r["sid"]: r for r in load(R2 / "judgments" / f)}, keys[k])
            for n, f, k in judges}

    overall = Counter(); dim = {d: Counter() for d in DIMS}
    per = {}
    for sc in scenarios():
        sid = sc["id"]
        per[sid] = {}
        for n, (rows, k) in data.items():
            r = rows.get(sid)
            if not r:
                per[sid][n] = "NA"; continue
            dec = k[sid].get(r["overall"], "TIE")
            per[sid][n] = dec
            overall[dec] += 1
            for d in DIMS:
                dim[d][k[sid].get(r["dims"].get(d, "平"), "TIE")] += 1

    lines = ["# 第二轮盲评汇总（事先确定的测试集）", "",
             "A = 直接写作；B = 启用 skill。judgeR2/R3 使用**标签互换**的材料。", "",
             "| 场景 | R1 | R2(换位) | R3(换位) | 票数 |", "|---|---|---|---|---|"]
    for sc in scenarios():
        sid = sc["id"]; v = per[sid]
        b = sum(1 for x in v.values() if x == "B"); a = sum(1 for x in v.values() if x == "A")
        lines.append(f"| {sid} {sc['title']} | {v.get('judgeR1')} | {v.get('judgeR2')} | "
                     f"{v.get('judgeR3')} | B{b}-A{a} |")
    b, a, t = overall["B"], overall["A"], overall["TIE"]
    lines += ["", f"**总评：B {b} / A {a} / 平 {t}**（{b+a+t} 次判断）", "",
              "| 维度 | B | A | 平 | B 胜率(去平) |", "|---|---|---|---|---|"]
    for d in DIMS:
        c = dim[d]
        rate = f"{c['B']/(c['B']+c['A']):.0%}" if (c["B"] + c["A"]) else "-"
        lines.append(f"| {CN[d]} | {c['B']} | {c['A']} | {c['TIE']} | {rate} |")
    (R2 / "judgments" / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (R2 / "judgments" / "summary.json").write_text(
        json.dumps({"overall": dict(overall), "dims": {d: dict(dim[d]) for d in DIMS},
                    "per_scene": per}, ensure_ascii=False, indent=2), encoding="utf-8")
    print("\n".join(lines))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["blind", "analyze", "aggregate"])
    args = ap.parse_args()
    {"blind": cmd_blind, "analyze": cmd_analyze, "aggregate": cmd_aggregate}[args.cmd](args)


if __name__ == "__main__":
    main()
