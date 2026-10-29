#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""interactive-fiction 状态管理（v0.1.1-beta，只用标准库）。

相对 v0.1.0 的变化：
- 故事内日历（年号/年/月/日 + day_index），跨年必须显式改元，年号越界直接报错
- 未结事项带 owner / deadline_day / trigger / overdue 四项
- 玩家持有物与已失去物分栏，禁止同一物品两边都有
- turn 可把关键事件写进 log.md
- save 分层输出，带长度上限与溢出裁剪

用法：
  python if_state.py init   --dir stories/诏书 --title 诏书 --genre history --era 隆庆 --year 6
  python if_state.py turn   --dir ... [--day-step 3] [--place 码头] [--beats "…"] [--event "…"]
  python if_state.py thread --dir ... --add "副本从哪来" --owner zhou --deadline-days 3 \
                            --trigger "司礼监来人" --overdue "副本被收缴"
  python if_state.py time   --dir ... --era 万历 --year 1 --month 1 --day 4
  python if_state.py check  --dir ... [--json]
  python if_state.py save   --dir ... [--max 600]
  python if_state.py load   --dir ...

退出码：0 正常 / 1 检查发现问题 / 2 参数或文件错误。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

RECENT_LIMIT = 8
CAST_REQUIRED = ("id", "name", "role", "want", "voice", "knows",
                 "does_not_know", "status", "last_seen", "with_player")
MIN_CAST = 3
ERA_MAX = {"隆庆": 6, "万历": 48}
ERA_NEXT = {"隆庆": ("万历", 1)}
SAVE_MAX = 600

WORLD_TPL = """# 世界 · {title}

## 一、铁律（不可改）
- 

## 二、历史与时代
- 年号：{era}（在位上限 {era_max} 年；次年改元）
- 架空分歧点（若有，逐条写清改了哪件史实）：

## 三、地理（≤7 个地点，写可达关系）
| 地点 | 在这能找到 | 到别处 | 谁的地盘 |
|---|---|---|---|
|  |  |  |  |

## 四、势力（3–5 个，写利益与手段）
| 势力 | 要什么 | 手段 | 与谁对立 |
|---|---|---|---|
|  |  |  |  |

## 五、矛盾
- 主线：
- 支线一：
- 支线二：

## 六、初始局势
- 

## 七、秘密分层
| 级别 | 内容 | 谁知道 | 什么条件下会漏 |
|---|---|---|---|
| 核心 |  |  |  |
| 中程 |  |  |  |
| 贴身 |  |  |  |

## 八、基调与严酷度
- 基调：{tone}
- 严酷度：{severity}
"""

STATE_TPL = {
    "version": 2,
    "title": "",
    "genre": "generic",
    "tone": "冷硬",
    "severity": "标准",
    "turn": 0,
    "calendar": {"era": "", "year": 1, "month": 1, "day": 1, "day_index": 1},
    "story_time": "",
    "scene": {"place": "", "present": [], "focus": ""},
    "threads": [],
    "player": {"name": "", "known": [], "unknown": [], "holds": [], "lost": [], "condition": ""},
}


def _p(x: str) -> Path:
    return Path(x).expanduser()


def read_json(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


def write_json(p: Path, data: dict) -> None:
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_state(d: Path) -> dict:
    p = d / "state.json"
    if not p.exists():
        sys.exit(f"找不到 {p}，先跑 init")
    st = read_json(p)
    st.setdefault("calendar", {"era": "", "year": 1, "month": 1, "day": 1, "day_index": 1})
    st.setdefault("player", {})
    st["player"].setdefault("holds", [])
    st["player"].setdefault("lost", [])
    return st


def fmt_time(cal: dict) -> str:
    era = cal.get("era") or "（未定年号）"
    y = cal.get("year", 1)
    ytxt = "元年" if y == 1 else f"{y}年"
    return f"{era}{ytxt}{cal.get('month',1)}月{cal.get('day',1)}日"


# ------------------------------------------------------------------ init
def cmd_init(a) -> int:
    d = _p(a.dir)
    if d.exists() and any(d.iterdir()) and not a.force:
        print(f"目录已存在且非空：{d}（加 --force 覆盖模板）")
        return 2
    d.mkdir(parents=True, exist_ok=True)

    (d / "world.md").write_text(
        WORLD_TPL.format(title=a.title, tone=a.tone, severity=a.severity,
                         era=a.era or "（未定）", era_max=ERA_MAX.get(a.era, "—")),
        encoding="utf-8")
    (d / "cast.json").write_text(
        json.dumps({"version": 1, "cast": []}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8")
    st = json.loads(json.dumps(STATE_TPL))
    st.update({"title": a.title, "genre": a.genre, "tone": a.tone, "severity": a.severity})
    st["calendar"].update({"era": a.era or "", "year": a.year or 1})
    st["story_time"] = fmt_time(st["calendar"])
    write_json(d / "state.json", st)
    (d / "log.md").write_text("# 事件\n\n", encoding="utf-8")
    (d / "recent.md").write_text("# 最近 8 轮\n\n", encoding="utf-8")
    print(f"已建立 {d}")
    print("下一步：填 world.md 的八张卡，再把 cast.json 里加 3 个以上 NPC。")
    return 0


# ------------------------------------------------------------------ turn
def trim_recent(text: str, limit: int = RECENT_LIMIT) -> str:
    parts = text.split("\n## ")
    head = parts[0].rstrip()
    blocks = parts[1:][-limit:]
    out = head + "\n"
    for b in blocks:
        out += "\n## " + b.strip() + "\n"
    return out


def cmd_turn(a) -> int:
    d = _p(a.dir)
    st = load_state(d)
    st["turn"] = int(st.get("turn", 0)) + 1
    n = st["turn"]

    cal = st["calendar"]
    if a.day_step:
        cal["day_index"] = int(cal.get("day_index", 1)) + a.day_step
        cal["day"] = int(cal.get("day", 1)) + a.day_step
        while cal["day"] > 30:
            cal["day"] -= 30
            cal["month"] = int(cal.get("month", 1)) + 1
        while cal["month"] > 12:
            cal["month"] -= 12
            cal["year"] = int(cal.get("year", 1)) + 1
        st["story_time"] = fmt_time(cal)

    if a.place:
        st["scene"]["place"] = a.place
    if a.focus:
        st["scene"]["focus"] = a.focus
    if a.present is not None:
        st["scene"]["present"] = [x.strip() for x in a.present.split(",") if x.strip()]
    write_json(d / "state.json", st)

    rp = d / "recent.md"
    txt = rp.read_text(encoding="utf-8") if rp.exists() else "# 最近 8 轮\n\n"
    block = [f"## 第{n}轮"]
    if a.place:
        block.append(f"场所：{a.place}")
    if a.beats:
        block.append(f"动作：{a.beats}")
    if a.words:
        block.append(f"用语：{a.words}")
    rp.write_text(trim_recent(txt.rstrip() + "\n\n" + "\n".join(block) + "\n"), encoding="utf-8")

    if a.event:
        lp = d / "log.md"
        lt = lp.read_text(encoding="utf-8") if lp.exists() else "# 事件\n\n"
        lt = lt.rstrip() + f"\n- [第{n}轮 · {st['story_time']}] {a.event}\n"
        lp.write_text(lt, encoding="utf-8")

    print(f"第 {n} 轮已记录 · {st['story_time']}")
    return 0


# ------------------------------------------------------------------ thread
def cmd_thread(a) -> int:
    d = _p(a.dir)
    st = load_state(d)
    ths = st.setdefault("threads", [])

    if a.list:
        if not ths:
            print("（没有未结事项）")
        for t in ths:
            dd = t.get("deadline_day")
            print(f"{t['id']} [{t['status']}] {t['title']} ← {t.get('owner','?')} "
                  f"· 到期第{dd}天 · 超期:{t.get('overdue','?')}")
        return 0

    if a.add:
        tid = f"t{len(ths) + 1}"
        dd = None
        if a.deadline_days:
            dd = int(st["calendar"].get("day_index", 1)) + a.deadline_days
        ths.append({
            "id": tid, "title": a.add, "status": "open",
            "since": st["turn"], "owner": a.owner or "",
            "deadline_day": dd, "trigger": a.trigger or "",
            "overdue": a.overdue or "",
        })
        write_json(d / "state.json", st)
        print(f"已加 {tid}：{a.add}（到期第{dd}天）" if dd else f"已加 {tid}：{a.add}")
        return 0

    if a.close:
        for t in ths:
            if t["id"] == a.close or t["title"] == a.close:
                t["status"] = "closed"
                t["closed_at"] = st["turn"]
                write_json(d / "state.json", st)
                print(f"已结 {t['id']}：{t['title']}")
                return 0
        print(f"没找到：{a.close}")
        return 2

    print("需要 --add / --close / --list 之一")
    return 2


# ------------------------------------------------------------------ time
def cmd_time(a) -> int:
    d = _p(a.dir)
    st = load_state(d)
    cal = st["calendar"]
    old_era = cal.get("era", "")

    if a.era and a.era != old_era:
        nxt = ERA_NEXT.get(old_era)
        if not nxt:
            print(f"警告：年号从「{old_era}」改为「{a.era}」，无改元规则，按架空处理")
        elif a.era != nxt[0]:
            print(f"错误：{old_era}之后应改元「{nxt[0]}」，不是「{a.era}」")
            return 2

    if a.era in ERA_MAX and (a.year or 1) > ERA_MAX[a.era]:
        nxt = ERA_NEXT.get(a.era)
        hint = f"，次年应改元「{nxt[0]}元年」" if nxt else ""
        print(f"错误：{a.era}只到第{ERA_MAX[a.era]}年{hint}")
        return 2

    cal.update({"era": a.era or old_era, "year": a.year or cal.get("year", 1),
                "month": a.month or 1, "day": a.day or 1})
    if not (1 <= cal["month"] <= 12):
        print("错误：月份必须在 1–12")
        return 2
    if not (1 <= cal["day"] <= 30):
        print("错误：日必须在 1–30（本模型每月按 30 天）")
        return 2
    st["story_time"] = fmt_time(cal)
    write_json(d / "state.json", st)
    print(f"时间已设为 {st['story_time']}（故事内第 {cal.get('day_index',1)} 天）")
    return 0


# ------------------------------------------------------------------ check
def cmd_check(a) -> int:
    d = _p(a.dir)
    errs: list[str] = []
    warns: list[str] = []

    st = load_state(d)
    cast = read_json(d / "cast.json").get("cast", []) if (d / "cast.json").exists() else []

    if len(cast) < MIN_CAST:
        warns.append(f"人物只有 {len(cast)} 个（建议 ≥{MIN_CAST}）")

    ids = {}
    for c in cast:
        miss = [k for k in CAST_REQUIRED if k not in c]
        if miss:
            errs.append(f"人物 {c.get('id','?')} 缺字段：{','.join(miss)}")
        ids[c.get("id")] = c
        if c.get("status") not in ("active", "away", "dead"):
            errs.append(f"人物 {c.get('id')} 的 status 非法：{c.get('status')}")
        if c.get("major") and c.get("status") == "dead" and c.get("with_player"):
            errs.append(f"重要人物 {c.get('id')} 已死但 with_player=true")

    present = st.get("scene", {}).get("present", [])
    for pid in present:
        if pid not in ids:
            errs.append(f"在场人物 {pid} 不在 cast.json")
        elif ids[pid].get("status") == "dead":
            errs.append(f"死者仍在场：{pid}")
    for cid, c in ids.items():
        if c.get("status") == "dead" and c.get("with_player"):
            errs.append(f"死者 with_player=true：{cid}")

    holds = st["player"].get("holds", [])
    lost = st["player"].get("lost", [])
    both = sorted(set(holds) & set(lost))
    if both:
        errs.append("同一物品同时在持有与已失去： " + "、".join(both))

    day = int(st["calendar"].get("day_index", 1))
    for t in st.get("threads", []):
        if t.get("status") not in ("open", "closed", "dormant"):
            errs.append(f"未结 {t.get('id')} 状态非法：{t.get('status')}")
        for f in ("owner", "trigger", "overdue"):
            if not t.get(f):
                warns.append(f"未结 {t.get('id')} 缺 {f}")
        dd = t.get("deadline_day")
        if t.get("status") == "open" and dd is not None and day > int(dd):
            errs.append(f"到期未处理：{t.get('id')} {t.get('title')}（第{dd}天到期，现第{day}天）")

    cal = st["calendar"]
    era = cal.get("era", "")
    if era in ERA_MAX and int(cal.get("year", 1)) > ERA_MAX[era]:
        errs.append(f"年号越界：{era}{cal.get('year')}年（{era}只有{ERA_MAX[era]}年）")
    if not (1 <= int(cal.get("month", 1)) <= 12):
        errs.append(f"月份越界：{cal.get('month')}")
    if not (1 <= int(cal.get("day", 1)) <= 30):
        errs.append(f"日期越界：{cal.get('day')}")

    rp = d / "recent.md"
    nblocks = rp.read_text(encoding="utf-8").count("\n## ") if rp.exists() else 0
    if nblocks > RECENT_LIMIT:
        errs.append(f"recent.md 有 {nblocks} 块，超过 {RECENT_LIMIT}")
    if st.get("turn", 0) < nblocks:
        errs.append("state.turn 小于 recent 块数")

    open_n = sum(1 for t in st.get("threads", []) if t.get("status") == "open")
    if a.json:
        print(json.dumps({"turn": st.get("turn"), "date": st["story_time"],
                          "open_threads": open_n, "cast": len(cast),
                          "errors": errs, "warnings": warns}, ensure_ascii=False, indent=2))
    else:
        print(f"{st['story_time']} · 第{st.get('turn')}轮 · 人物{len(cast)} · 未结{open_n}")
        for e in errs:
            print(f"  ✗ {e}")
        for w in warns:
            print(f"  ! {w}")
        if not errs:
            print("  ✓ 检查通过" + ("（有提醒）" if warns else ""))
    return 1 if errs else 0


# ------------------------------------------------------------------ save / load
def _cut(text: str, limit: int) -> tuple[str, bool]:
    if len(text) <= limit:
        return text, False
    cut = text[:limit].rsplit("\n", 1)[0]
    return cut + "\n[已裁剪：超出长度上限]", True


def cmd_save(a) -> int:
    d = _p(a.dir)
    st = load_state(d)
    cast = read_json(d / "cast.json").get("cast", []) if (d / "cast.json").exists() else []

    present = [c for c in cast if c.get("with_player") or c.get("id") in st["scene"].get("present", [])]
    opens = [t for t in st.get("threads", []) if t.get("status") == "open"]

    # 分层：必需 > 次要 > 可丢
    core = [
        f"# 恢复卡 · {st.get('title','')} · 第{st.get('turn')}轮",
        f"时间：{st['story_time']} ｜ {st['scene'].get('place','')}",
        "在场：" + ("；".join(
            f"{c['name']}（{c.get('voice','')[:12]}｜{(c.get('debt') or {}).get('type','—')}）"
            for c in present) or "无"),
        "未结：" + ("；".join(
            f"{t['id']}{t['title']}（{t.get('owner','?')}·第{t.get('deadline_day','—')}天）"
            for t in opens) or "无"),
        f"玩家：{st['player'].get('name','') or '（未命名）'}；"
        f"持有：{'、'.join(st['player'].get('holds', [])) or '无'}；"
        f"已失：{'、'.join(st['player'].get('lost', [])) or '无'}",
        "压力：" + (opens[0].get("overdue", "") if opens else "无"),
    ]
    opt = [
        "已知：" + ("；".join(st["player"].get("known", [])[:5]) or "无"),
        "关系：" + ("；".join(
            f"{c['name']}·{(c.get('debt') or {}).get('type','—')}·{(c.get('debt') or {}).get('note','')[:14]}"
            for c in present) or "无"),
    ]
    text = "\n".join(core + opt) + "\n"
    text, cut = _cut(text, a.max)
    (d / "SAVE.md").write_text(text, encoding="utf-8")
    print(text)
    print(f"[长度 {len(text)} / 上限 {a.max}{' · 已裁剪' if cut else ''}]")
    return 0


def cmd_load(a) -> int:
    p = _p(a.dir) / "SAVE.md"
    if not p.exists():
        print("还没有 SAVE.md，先跑 save")
        return 2
    print(p.read_text(encoding="utf-8"))
    return 0


# ------------------------------------------------------------------ main
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="interactive-fiction 状态管理")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("init"); p.add_argument("--dir", required=True)
    p.add_argument("--title", default="未命名"); p.add_argument("--genre", default="generic")
    p.add_argument("--tone", default="冷硬"); p.add_argument("--severity", default="标准")
    p.add_argument("--era", default=""); p.add_argument("--year", type=int, default=1)
    p.add_argument("--force", action="store_true"); p.set_defaults(func=cmd_init)

    p = sub.add_parser("turn"); p.add_argument("--dir", required=True)
    p.add_argument("--place"); p.add_argument("--focus"); p.add_argument("--present")
    p.add_argument("--beats"); p.add_argument("--words")
    p.add_argument("--day-step", type=int, default=0)
    p.add_argument("--event")
    p.set_defaults(func=cmd_turn)

    p = sub.add_parser("thread"); p.add_argument("--dir", required=True)
    p.add_argument("--add"); p.add_argument("--owner"); p.add_argument("--deadline-days", type=int)
    p.add_argument("--trigger"); p.add_argument("--overdue")
    p.add_argument("--close"); p.add_argument("--list", action="store_true")
    p.set_defaults(func=cmd_thread)

    p = sub.add_parser("time"); p.add_argument("--dir", required=True)
    p.add_argument("--era"); p.add_argument("--year", type=int)
    p.add_argument("--month", type=int); p.add_argument("--day", type=int)
    p.set_defaults(func=cmd_time)

    p = sub.add_parser("check"); p.add_argument("--dir", required=True)
    p.add_argument("--json", action="store_true"); p.set_defaults(func=cmd_check)

    p = sub.add_parser("save"); p.add_argument("--dir", required=True)
    p.add_argument("--max", type=int, default=SAVE_MAX); p.set_defaults(func=cmd_save)
    p = sub.add_parser("load"); p.add_argument("--dir", required=True); p.set_defaults(func=cmd_load)

    a = ap.parse_args(argv)
    try:
        return a.func(a)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"错误：{e}")
        return 2


if __name__ == "__main__":
    sys.exit(main())
