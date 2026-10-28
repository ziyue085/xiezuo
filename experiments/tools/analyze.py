#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""对 A/B 两组产出做客观侧统计：表层指标 + 硬性约束检查。

输出：
  experiments/metrics.csv        每个 (场景, 组) 一行的指标
  experiments/checks.csv         约束检查结果（True/False）
  experiments/metrics.md         便于阅读的对照表

注意：这些数字**不是质量分**。它们只回答"这段文字在表层上有什么特征"，
以及"任务里的硬性要求有没有被遵守"。质量判断在盲评里。
"""

from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCEN = ROOT / "literary-craft" / "tests" / "scenarios" / "scenarios.json"
RUNS = ROOT / "experiments" / "runs"
sys.path.insert(0, str(ROOT / "literary-craft" / "scripts"))

import craft_lint as cl  # noqa: E402

CJK = re.compile(r"[\u4e00-\u9fff]")
NUM = re.compile(r"\d+(?:\.\d+)?")
# 中文数字 + 单位（"两块二""四十六斤""三千余口"），中文写作里比阿拉伯数字更常见
CN_NUM = re.compile(
    r"[一二三四五六七八九十百千万亿零两半]+"
    r"(?:块|元|毛|角|斤|两|个|张|袋|桶|碗|文|贯|石|斗|亩|人|户|里|年|天|日|月|分|钱|口|余)"
)
MONEY = re.compile(r"\d+(?:\.\d+)?\s*(?:元|块|毛|角|斤|两|个|张|袋|桶|碗|文|贯|石|斗)")


def chars(t: str) -> int:
    return len(CJK.findall(t))


def load(sid: str, arm: str) -> str:
    p = RUNS / sid / f"{arm}.md"
    return p.read_text(encoding="utf-8") if p.exists() else ""


def run_checks(sc: dict, text: str) -> dict:
    c = sc.get("checks", {})
    out = {"chars": chars(text)}
    out["min_chars_ok"] = out["chars"] >= c.get("min_chars", 0)
    if "max_chars" in c:
        out["max_chars_ok"] = out["chars"] <= c["max_chars"]
    if "must_keep" in c:
        kept = [k for k in c["must_keep"] if any(x and x in text for x in k.split("|"))]
        out["must_keep_hit"] = f"{len(kept)}/{len(c['must_keep'])}"
        out["must_keep_missing"] = ",".join(
            k for k in c["must_keep"] if not any(x and x in text for x in k.split("|"))
        )
    if "must_not" in c:
        # 润色任务允许"改动说明"里出现被删掉的词，因此只在正文里查禁用词
        body = re.split(r"\n\s*(?:改动说明|修改说明|改了什么)", text)[0] if sc["task"] == "revise" else text
        out["body_chars"] = chars(body)
        bad = [k for k in c["must_not"] if k in body]
        out["must_not_hit"] = f"{len(bad)}/{len(c['must_not'])}"
        out["must_not_words"] = ",".join(bad)
    if "min_numbers" in c:
        n = len(NUM.findall(text)) + len(CN_NUM.findall(text))
        out["numbers"] = n
        out["min_numbers_ok"] = n >= c["min_numbers"]
    if "min_amounts" in c:
        n = len(MONEY.findall(text)) + len(CN_NUM.findall(text))
        out["amounts"] = n
        out["min_amounts_ok"] = n >= c["min_amounts"]
    return out


def main() -> None:
    data = json.loads(SCEN.read_text(encoding="utf-8"))
    rows, checks = [], []
    for sc in data["scenarios"]:
        for arm in ("A", "B"):
            text = load(sc["id"], arm)
            if not text:
                continue
            res = cl.analyze(text, mode=sc["mode"],
                             era="ancient" if sc["mode"] == "history" else "")
            m = res["metrics"]
            row = {"sid": sc["id"], "mode": sc["mode"], "arm": arm,
                   "char": m["chars"], "sent_mean": m["sent_mean"],
                   "sent_cv": m["sent_cv"], "short_pct": m["short_pct"],
                   "long_pct": m["long_pct"], "para_cv": m["para_cv"],
                   "single_para_pct": m["single_sent_para_pct"],
                   "dialogue_pct": m["dialogue_pct"],
                   "emotion_per_k": m["emotion_naming_per_k"],
                   "body_per_k": m["body_reaction_per_k"],
                   "cliche_per_k": m["cliche_per_k"],
                   "explain_per_k": m["explain_per_k"],
                   "abstract_per_k": m["abstract_per_k"],
                   "not_a_but_b": m["not_a_but_b"], "parallel3": m["parallel3"],
                   "dash_per_k": m["dash_per_k"],
                   "flags": len(res["flags"]),
                   "flag_codes": "|".join(f["code"] for f in res["flags"])}
            rows.append(row)
            c = run_checks(sc, text)
            c.update({"sid": sc["id"], "arm": arm})
            checks.append(c)

    # csv
    keys = ["sid", "mode", "arm", "char", "sent_mean", "sent_cv", "short_pct",
            "long_pct", "para_cv", "single_para_pct", "dialogue_pct",
            "emotion_per_k", "body_per_k", "cliche_per_k", "explain_per_k",
            "abstract_per_k", "not_a_but_b", "parallel3", "dash_per_k",
            "flags", "flag_codes"]
    with (ROOT / "experiments" / "metrics.csv").open("w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)

    ckeys = ["sid", "arm", "chars", "min_chars_ok", "max_chars_ok",
             "must_keep_hit", "must_keep_missing", "must_not_hit", "must_not_words",
             "numbers", "min_numbers_ok", "amounts", "min_amounts_ok"]
    with (ROOT / "experiments" / "checks.csv").open("w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=ckeys, extrasaction="ignore")
        w.writeheader()
        w.writerows(checks)

    # markdown
    sids = [sc["id"] for sc in data["scenarios"]]
    line = ["| 场景 | 组 | 字数 | 句长CV | 短句% | 对话% | 情绪命名/千 | 套话/千 | 提示数 |",
            "|---|---|---|---|---|---|---|---|---|"]
    by = {(r["sid"], r["arm"]): r for r in rows}
    for sid in sids:
        for arm in ("A", "B"):
            r = by.get((sid, arm))
            if not r:
                continue
            line.append(
                f"| {sid} | {arm} | {r['char']} | {r['sent_cv']} | {r['short_pct']} | "
                f"{r['dialogue_pct']} | {r['emotion_per_k']} | {r['cliche_per_k']} | {r['flags']} |"
            )
    (ROOT / "experiments" / "metrics.md").write_text("\n".join(line) + "\n", encoding="utf-8")
    print("\n".join(line))
    print(f"\nrows={len(rows)} checks={len(checks)}")


if __name__ == "__main__":
    main()
