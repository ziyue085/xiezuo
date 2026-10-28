#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""craft_lint.py — 中文文本表层体检（只提示，不打分）

设计立场
--------
这个脚本**不能判断文本好坏**。它只做一件事：把"极端值"标出来，交给人工判断。
理由：句长均匀、形容词多、套话密集，在特定语境下都可能是正确选择。
任何"分数"都会诱导用户为分数写作，那是本末倒置。

因此：
  * 所有检查项都是 advisory，没有一项判定"不合格"。
  * 阈值取的是**极端值**，不是"优秀值"。落在阈值内不代表好。
  * --json 输出原始指标，方便做 A/B 对照实验的客观侧数据。

退出码
------
  0  未触发任何提示
  1  触发了提示（**不代表文本差**，需人工逐条判断）
  2  输入或参数错误

用法
----
  python craft_lint.py --file draft.txt
  python craft_lint.py --file draft.txt --json
  python craft_lint.py --file draft.txt --mode fiction
  python craft_lint.py --file draft.txt --mode history --era ancient
"""

from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
from pathlib import Path

CJK_RE = re.compile(r"[\u4e00-\u9fff]")

# ---------------------------------------------------------------- 词表
# 情绪命名（直接说出情绪词/感受词，而非给出证据）
EMOTION_NAMING = [
    "感到", "觉得", "心中", "心里", "内心", "莫名", "说不出的", "五味杂陈",
    "悲伤", "痛苦", "孤独", "绝望", "无助", "温暖", "幸福", "愤怒", "恐惧",
    "欣慰", "惆怅", "失落", "委屈", "心酸", "感动", "压抑", "煎熬",
]
# 身体反应（比命名强，但仍易套路；单列为"有效通道"，不计入命名）
BODY_REACTION = [
    "手心", "出汗", "喉咙", "眼眶", "鼻子", "胸口", "心跳", "呼吸", "发抖",
    "手抖", "后背", "胃里", "腿软", "牙关", "耳鸣", "脸烫", "指尖",
]
DEGREE_ADV = [
    "非常", "极其", "十分", "格外", "异常", "无比", "极度", "分外",
    "特别", "十二分", "万分", "分外", "绝顶",
]
EXPLAIN_MARKERS = [
    "这说明", "这意味着", "也就是说", "换句话说", "仿佛在", "似乎在",
    "好像在诉说", "或许这就是", "正是因为", "可见", "不难看出", "这些都表明",
]
CLICHE = [
    "不禁", "仿佛", "似乎", "宛如", "犹如", "一丝", "一抹", "一缕", "不由得",
    "油然而生", "不寒而栗", "历历在目", "记忆犹新", "浮想联翩", "感慨万千",
    "叹为观止", "美不胜收", "心旷神怡", "栩栩如生", "跃然纸上", "扑面而来",
    "难以言喻", "无以言表", "意味深长", "耐人寻味", "发人深省", "空气仿佛凝固",
    "时间仿佛静止", "恍如隔世", "若有所失", "若有所思",
]
ABSTRACT_SUFFIX_RE = re.compile(
    r"[性度]|主义|精神|意义|价值|命运|时代|灵魂|本质|力量|气息|氛围|气息"
)
QUANTIFIERS = list("个只条张文本件把斤里米年天日月岁步间座头匹碗杯根支片层场顿双副")
SENSORY = {
    "视觉": list("看见光色影亮暗"),
    "听觉": list("听声响静噪"),
    "嗅觉": list("闻香味臭"),
    "味觉": list("尝甜苦咸辣酸"),
    "触觉": list("摸冷热硬软湿疼痒"),
}
DIALOGUE_TAGS = ["说道", "说", "道", "问", "答", "喊", "叫", "笑", "骂", "嘟囔"]
MODERN_VOCAB = [
    "干部", "单位", "领导", "项目", "效率", "经济", "社会", "心理", "科学",
    "统计", "数据", "系统", "机制", "基层", "组织", "阶级", "信息", "资源",
    "管理", "结构", "模式", "流程", "指标",
]

SENT_END = "。！？!?"


# ---------------------------------------------------------------- 基础解析
def read_text(path: str) -> str:
    raw = Path(path).read_bytes()
    for enc in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    raise SystemExit(f"[error] 无法解码文件：{path}")


def split_paragraphs(text: str) -> list[str]:
    blocks = re.split(r"\n\s*\n", text.strip())
    if len(blocks) <= 1:
        blocks = [ln for ln in text.splitlines() if ln.strip()]
    out = []
    for b in blocks:
        b = b.strip()
        if b:
            # 段内软换行合并
            out.append(re.sub(r"\s*\n\s*", "", b))
    return out


def split_sentences(para: str) -> list[str]:
    parts = re.findall(rf"[^{SENT_END}]+[{SENT_END}]*", para)
    return [p.strip() for p in parts if CJK_RE.search(p)]


def cjk_len(s: str) -> int:
    return len(CJK_RE.findall(s))


def dialogue_chars(text: str) -> int:
    total = 0
    for pat in (r"“([^”]*)”", r"「([^」]*)」"):
        total += sum(cjk_len(m) for m in re.findall(pat, text))
    return total


def percentile(vals: list[int], q: float) -> float:
    if not vals:
        return 0.0
    s = sorted(vals)
    k = (len(s) - 1) * q
    lo, hi = int(k), min(int(k) + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (k - lo)


def cv(vals: list[float]) -> float:
    if len(vals) < 2:
        return 0.0
    m = statistics.fmean(vals)
    return statistics.pstdev(vals) / m if m else 0.0


def count_terms(text: str, terms: list[str]) -> int:
    return sum(text.count(t) for t in terms)


def top_ngrams(text: str, n: int = 4, top: int = 5) -> list[list]:
    runs = re.findall(r"[\u4e00-\u9fff]+", text)
    freq: dict[str, int] = {}
    for run in runs:
        for i in range(len(run) - n + 1):
            g = run[i:i + n]
            freq[g] = freq.get(g, 0) + 1
    items = [(g, c) for g, c in freq.items() if c >= 3]
    items.sort(key=lambda x: (-x[1], x[0]))
    return [[g, c] for g, c in items[:top]]


def parallel_triples(sentences: list[str]) -> int:
    """粗略识别"三连排比"。

    只认结构性重复：连续三个逗号分句，长度接近（差≤3），且
    同头（首字相同）或同尾（末字相同）或同带"的"。
    单纯的短句并列不判——那可能只是正常叙述。
    """
    hits = 0
    for s in sentences:
        segs = [x.strip() for x in re.split(r"[，、]", s) if cjk_len(x) >= 3]
        for i in range(len(segs) - 2):
            trio = segs[i:i + 3]
            lens = [cjk_len(x) for x in trio]
            if max(lens) - min(lens) > 3:
                continue
            same_head = len({x[0] for x in trio}) == 1
            same_tail = len({x[-1] for x in trio}) == 1
            all_de = all("的" in x for x in trio)
            if same_head or same_tail or all_de:
                hits += 1
                break
    return hits


def count_pattern(text: str, pat: str) -> int:
    return len(re.findall(pat, text))


# ---------------------------------------------------------------- 主分析
def analyze(text: str, mode: str = "generic", era: str = "") -> dict:
    paras = split_paragraphs(text)
    sents: list[str] = []
    para_sent_counts: list[int] = []
    for p in paras:
        ps = split_sentences(p)
        para_sent_counts.append(len(ps))
        sents.extend(ps)

    n_chars = cjk_len(text)
    sent_lens = [cjk_len(s) for s in sents if cjk_len(s) > 0]
    para_lens = [cjk_len(p) for p in paras]
    per_k = (lambda x: round(x * 1000 / n_chars, 2)) if n_chars else (lambda x: 0.0)

    dlg = dialogue_chars(text)
    total_sent = len(sent_lens) or 1

    m = {
        "chars": n_chars,
        "paragraphs": len(paras),
        "sentences": len(sent_lens),
        "sent_mean": round(statistics.fmean(sent_lens), 1) if sent_lens else 0,
        "sent_sd": round(statistics.pstdev(sent_lens), 1) if len(sent_lens) > 1 else 0,
        "sent_cv": round(cv([float(x) for x in sent_lens]), 2),
        "sent_p10": round(percentile(sent_lens, 0.1), 1),
        "sent_p50": round(percentile(sent_lens, 0.5), 1),
        "sent_p90": round(percentile(sent_lens, 0.9), 1),
        "sent_max": max(sent_lens) if sent_lens else 0,
        "short_pct": round(100 * sum(1 for x in sent_lens if x <= 12) / total_sent, 1),
        "long_pct": round(100 * sum(1 for x in sent_lens if x >= 40) / total_sent, 1),
        "para_mean": round(statistics.fmean(para_lens), 1) if para_lens else 0,
        "para_cv": round(cv([float(x) for x in para_lens]), 2),
        "single_sent_para_pct": round(
            100 * sum(1 for c in para_sent_counts if c == 1) / max(len(paras), 1), 1
        ),
        "dialogue_pct": round(100 * dlg / n_chars, 1) if n_chars else 0.0,
        "de_per_k": per_k(text.count("的")),
        "degree_per_k": per_k(count_terms(text, DEGREE_ADV)),
        "emotion_naming_per_k": per_k(count_terms(text, EMOTION_NAMING)),
        "body_reaction_per_k": per_k(count_terms(text, BODY_REACTION)),
        "explain_per_k": per_k(count_terms(text, EXPLAIN_MARKERS)),
        "cliche_per_k": per_k(count_terms(text, CLICHE)),
        "abstract_per_k": per_k(len(ABSTRACT_SUFFIX_RE.findall(text))),
        "not_a_but_b": count_pattern(text, r"不是[^。！？]{0,20}?而是")
        + count_pattern(text, r"并非[^。！？]{0,20}?而是"),
        "parallel3": parallel_triples(sents),
        "dash_per_k": per_k(text.count("——")),
        "ellipsis_per_k": per_k(text.count("……")),
        "exclaim_per_k": per_k(text.count("！") + text.count("!")),
        "digit_count": len(re.findall(r"\d", text)),
        "quantifier_per_k": per_k(sum(text.count(q) for q in QUANTIFIERS)),
        "dialogue_tags": {t: text.count(t) for t in DIALOGUE_TAGS if text.count(t)},
        "sensory": {
            k: sum(text.count(c) for c in v) for k, v in SENSORY.items()
        },
        "top_4grams": top_ngrams(text, 4, 5),
    }

    flags: list[dict] = []

    # 密度指标在短文本上方差很大，因此每条都同时要求"绝对次数"达标，
    # 否则 200 字的片段会因为一个破折号被判为异常。
    n_degree = count_terms(text, DEGREE_ADV)
    n_emotion = count_terms(text, EMOTION_NAMING)
    n_body = count_terms(text, BODY_REACTION)
    n_explain = count_terms(text, EXPLAIN_MARKERS)
    n_cliche = count_terms(text, CLICHE)
    n_abstract = len(ABSTRACT_SUFFIX_RE.findall(text))
    n_dash = text.count("——")

    def flag(code: str, msg: str, advice: str) -> None:
        flags.append({"code": code, "msg": msg, "advice": advice})

    if m["sentences"] >= 12:
        if m["sent_cv"] < 0.35:
            flag("RHYTHM_FLAT",
                 f"句长离散度低（CV={m['sent_cv']}，短句 {m['short_pct']}%、长句 {m['long_pct']}%）",
                 "整段长度接近，读者感觉不到速度变化。检查关键处是否该断句。")
        if m["short_pct"] < 6 and m["sent_mean"] > 28:
            flag("NO_BREAK",
                 f"短句仅 {m['short_pct']}%，平均句长 {m['sent_mean']} 字",
                 "长时间没有断点，情绪和动作会糊在一起。")

    if m["degree_per_k"] >= 12 and n_degree >= 6:
        flag("DEGREE_HEAVY",
             f"程度副词 {n_degree} 次（{m['degree_per_k']}/千字）",
             "「很／非常／格外」在替形容词加力。换成可观察的事实更有效。")

    if m["emotion_naming_per_k"] >= 6 and n_emotion >= 4 and n_body < 1:
        flag("EMOTION_NAMED",
             f"情绪命名 {n_emotion} 次（{m['emotion_naming_per_k']}/千字），身体反应 0 次",
             "情绪全靠命名，读者无参与空间。改成动作偏差或注意力错位。")

    if m["explain_per_k"] >= 6 and n_explain >= 3:
        flag("OVER_EXPLAIN",
             f"解释性标记 {n_explain} 次（{m['explain_per_k']}/千字）",
             "在给读者解释刚发生的事。多数情况删掉解释句，只留后果。")

    if m["cliche_per_k"] >= 4 and n_cliche >= 3:
        flag("CLICHE",
             f"套话 {n_cliche} 次（{m['cliche_per_k']}/千字），首次命中：{_first_hit(text, CLICHE)}",
             "「仿佛／不禁／一丝」这类柔光词，删掉后句子通常更硬。")

    if m["not_a_but_b"] >= 2:
        flag("NOT_A_BUT_B",
             f"「不是…而是…」出现 {m['not_a_but_b']} 次",
             "该句式容易伪造思辨感。直接说结论，或让事实完成对比。")

    if m["parallel3"] >= 2:
        flag("PARALLEL3",
             f"疑似三连排比 {m['parallel3']} 处",
             "三项同构排比是抒情偷懒的标准配置。留一项，或让三项长短不齐。")

    if m["dash_per_k"] >= 5 and n_dash >= 3:
        flag("DASH_HEAVY",
             f"破折号 {n_dash} 次（{m['dash_per_k']}/千字）",
             "破折号后面常是作者忍不住补的抒情，试着删掉后半句。")

    if m["paragraphs"] >= 5 and m["single_sent_para_pct"] == 0 and m["para_cv"] < 0.35:
        flag("PARA_FLAT",
             f"段长接近（CV={m['para_cv']}），且无单句成段",
             "段落没有节拍。关键处让一句独立成段，或把过渡段压成一句。")

    if m["top_4grams"] and m["top_4grams"][0][1] >= 4:
        g, c = m["top_4grams"][0]
        flag("REPEAT",
             f"四字片段「{g}」重复 {c} 次",
             "同一措辞反复出现，读起来像口头禅。")

    if m["abstract_per_k"] >= 25 and n_abstract >= 8:
        flag("ABSTRACT_HEAVY",
             f"抽象化后缀 {n_abstract} 次（{m['abstract_per_k']}/千字）",
             "抽象名词密集时，句子容易变成议论。让具体的人做主语。")

    if mode == "fiction" and m["chars"] >= 300 and m["dialogue_pct"] < 3:
        flag("NO_DIALOGUE",
             f"对话占比仅 {m['dialogue_pct']}%",
             "小说几乎无对话时，确认是有意为之（独白式短篇），否则人物会失去声音。")

    if mode == "history" and era == "ancient":
        hits = [w for w in MODERN_VOCAB if text.count(w)]
        if hits:
            flag("ANACHRONISM",
                 f"古代题材出现现代词汇：{'、'.join(hits[:8])}",
                 "逐条确认是否为时代错置；叙述者评论可用，人物口中不可用。")

    # 排序：稳定输出
    flags.sort(key=lambda x: x["code"])

    return {
        "file_meta": {"mode": mode, "era": era or "-"},
        "metrics": m,
        "flags": flags,
        "note": "本报告只标极端值，不打分。命中≠差，未命中≠好。",
    }


def _first_hit(text: str, terms: list[str]) -> str:
    best = (len(text) + 1, "")
    for t in terms:
        i = text.find(t)
        if 0 <= i < best[0]:
            best = (i, t)
    return best[1] or "-"


# ---------------------------------------------------------------- 输出
def render_text(res: dict) -> str:
    m = res["metrics"]
    lines = []
    lines.append("== 表层指标（描述性，非评分） ==")
    lines.append(
        f"汉字 {m['chars']}｜段 {m['paragraphs']}｜句 {m['sentences']}"
        f"｜对话占比 {m['dialogue_pct']}%"
    )
    lines.append(
        f"句长 均值 {m['sent_mean']}｜中位 {m['sent_p50']}｜P90 {m['sent_p90']}"
        f"｜最长 {m['sent_max']}｜CV {m['sent_cv']}"
        f"｜短句 {m['short_pct']}%｜长句 {m['long_pct']}%"
    )
    lines.append(
        f"段长 均值 {m['para_mean']}｜CV {m['para_cv']}"
        f"｜单句段 {m['single_sent_para_pct']}%"
    )
    lines.append(
        "密度（每千字）  的 {de}｜程度副词 {deg}｜情绪命名 {emo}｜身体反应 {body}"
        "｜解释 {exp}｜套话 {cli}｜抽象 {abs_}".format(
            de=m["de_per_k"], deg=m["degree_per_k"], emo=m["emotion_naming_per_k"],
            body=m["body_reaction_per_k"], exp=m["explain_per_k"],
            cli=m["cliche_per_k"], abs_=m["abstract_per_k"],
        )
    )
    lines.append(
        f"其他 破折号 {m['dash_per_k']}｜省略号 {m['ellipsis_per_k']}"
        f"｜感叹号 {m['exclaim_per_k']}｜数字 {m['digit_count']}"
        f"｜不是A而是B {m['not_a_but_b']}｜三连排比 {m['parallel3']}"
    )
    if m["top_4grams"]:
        lines.append("高频四字片段 " + "，".join(f"{g}×{c}" for g, c in m["top_4grams"]))
    sensory = m["sensory"]
    if sum(sensory.values()):
        lines.append("感官通道 " + "，".join(f"{k}{v}" for k, v in sensory.items()))

    lines.append("")
    if not res["flags"]:
        lines.append("== 提示 ==  无。仍然需要人读一遍。")
    else:
        lines.append(f"== 提示 {len(res['flags'])} 条（需人工判断，不代表不合格） ==")
        for f in res["flags"]:
            lines.append(f"[{f['code']}] {f['msg']}")
            lines.append(f"    → {f['advice']}")
    lines.append("")
    lines.append(res["note"])
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="中文文本表层体检（advisory）")
    ap.add_argument("--file", required=True, help="待检查文本（utf-8 / gbk）")
    ap.add_argument("--mode", default="generic",
                    choices=["generic", "fiction", "history", "essay", "revise", "edit"])
    ap.add_argument("--era", default="", choices=["", "ancient"], help="历史题材的时代设定")
    ap.add_argument("--json", action="store_true", help="输出 JSON")
    args = ap.parse_args(argv)

    try:
        text = read_text(args.file)
    except Exception as exc:  # noqa: BLE001
        print(f"[error] {exc}", file=sys.stderr)
        return 2

    if cjk_len(text) < 50:
        print("[error] 文本过短（<50 汉字），指标无意义", file=sys.stderr)
        return 2

    res = analyze(text, mode=args.mode, era=args.era)
    res["file_meta"]["path"] = str(Path(args.file))

    if args.json:
        print(json.dumps(res, ensure_ascii=False, indent=2))
    else:
        print(render_text(res))

    return 1 if res["flags"] else 0


if __name__ == "__main__":
    sys.exit(main())
