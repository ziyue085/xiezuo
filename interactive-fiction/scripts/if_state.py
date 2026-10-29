#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""interactive-fiction 状态管理（只用标准库）。

用法：
  python if_state.py init   --dir stories/诏书 --title 诏书 --genre history
  python if_state.py turn   --dir stories/诏书 --place 档案房 --beats "周有德锁门；玩家抄日期"
  python if_state.py thread --dir stories/诏书 --add "副本从哪来" --pressure "三日内来取"
  python if_state.py thread --dir stories/诏书 --close t1
  python if_state.py check  --dir stories/诏书
  python if_state.py save   --dir stories/诏书
  python if_state.py load   --dir stories/诏书

退出码：0 正常 / 1 检查发现问题 / 2 参数或文件错误。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

RECENT_LIMIT = 8
CAST_KEYS = ("id", "name", "role", "want", "voice", "knows",
             "does_not_know", "status", "last_seen", "with_player")

WORLD_TPL = """# 世界 · {title}

## 一、铁律（不可改）
- 

## 二、历史与时代
- 

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
    "version": 1,
    "title": "",
    "genre": "generic",
    "tone": "冷硬",
    "severity": "标准",
    "turn": 0,
    "story_time": "",
    "scene": {"place": "", "present": [], "focus": ""},
    "threads": [],
    "player": {"name": "", "known": [], "unknown": [], "assets": [], "condition": ""},
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
    return read_json(p)


# ------------------------------------------------------------------ init
def cmd_init(a) -> int:
    d = _p(a.dir)
    if d.exists() and any(d.iterdir()) and not a.force:
        print(f"目录已存在且非空：{d}（加 --force 覆盖模板）")
        return 2
    d.mkdir(parents=True, exist_ok=True)

    (d / "world.md").write_text(
        WORLD_TPL.format(title=a.title, tone=a.tone, severity=a.severity), encoding="utf-8")
    (d / "cast.json").write_text(
        json.dumps({"version": 1, "cast": []}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8")
    st = dict(STATE_TPL)
    st.update({"title": a.title, "genre": a.genre, "tone": a.tone, "severity": a.severity})
    write_json(d / "state.json", st)
    (d / "log.md").write_text("# 事件\n\n", encoding="utf-8")
    (d / "recent.md").write_text("# 最近 8 轮\n\n", encoding="utf-8")
    print(f"已建立 {d}")
    print("下一步：填 world.md 的八张卡，再把 cast.json 里加 3–5 个 NPC。")
    return 0


# ------------------------------------------------------------------ turn
def trim_recent(text: str, limit: int = RECENT_LIMIT) -> str:
    parts = text.split("\n## ")
    head = parts[0].rstrip()
    blocks = parts[1:]
    blocks = blocks[-limit:]
    out = head + "\n"
    for b in blocks:
        out += "\n## " + b.strip() + "\n"
    return out


def cmd_turn(a) -> int:
    d = _p(a.dir)
    st = load_state(d)
    st["turn"] = int(st.get("turn", 0)) + 1
    n = st["turn"]

    if a.place:
        st["scene"]["place"] = a.place
    if a.time:
        st["story_time"] = a.time
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
    txt = trim_recent(txt.rstrip() + "\n\n" + "\n".join(block) + "\n")
    rp.write_text(txt, encoding="utf-8")

    print(f"第 {n} 轮已记录。")
    return 0


# ------------------------------------------------------------------ thread
def cmd_thread(a) -> int:
    d = _p(a.dir)
    st = load_state(d)
    ths = st.setdefault("threads", [])

    if a.list:
        if not ths:
            print("（没有未结线索）")
        for t in ths:
            print(f"{t['id']}  [{t['status']}]  {t['title']}  ← {t.get('pressure','')}")
        return 0

    if a.add:
        tid = f"t{len(ths) + 1}"
        ths.append({"id": tid, "title": a.add, "status": "open",
                    "since": st["turn"], "pressure": a.pressure or ""})
        write_json(d / "state.json", st)
        print(f"已加 {tid}：{a.add}")
        return 0

    if a.close:
        for t in ths:
            if t["id"] == a.close or t["title"] == a.close:
                t["status"] = "closed"
                t["closed_at"] = st["turn"]
                write_json(d / "state.json", st)
                print(f"已结 {t['id']}：{t['title']}")
                return 0
        print(f"没找到线索：{a.close}")
        return 2

    print("需要 --add / --close / --list 之一")
    return 2


# ------------------------------------------------------------------ check
def cmd_check(a) -> int:
    d = _p(a.dir)
    issues: list[str] = []

    st = load_state(d)
    cast_p = d / "cast.json"
    cast = read_json(cast_p).get("cast", []) if cast_p.exists() else []

    if not cast:
        issues.append("cast.json 里没有人物（至少 3 个核心 NPC）")

    ids = {}
    for c in cast:
        miss = [k for k in CAST_KEYS if k not in c]
        if miss:
            issues.append(f"人物 {c.get('id','?')} 缺字段：{','.join(miss)}")
        ids[c.get("id")] = c
        if c.get("status") not in ("active", "away", "dead"):
            issues.append(f"人物 {c.get('id')} 的 status 非法：{c.get('status')}")

    present = st.get("scene", {}).get("present", [])
    for pid in present:
        if pid not in ids:
            issues.append(f"场景在场人物 {pid} 不在 cast.json 里")
        elif ids[pid].get("status") == "dead":
            issues.append(f"死者仍在场：{pid}（已 dead，不能出现在 present）")

    for t in st.get("threads", []):
        if t.get("status") not in ("open", "closed", "dormant"):
            issues.append(f"线索 {t.get('id')} 状态非法：{t.get('status')}")

    recent_p = d / "recent.md"
    nblocks = 0
    if recent_p.exists():
        nblocks = recent_p.read_text(encoding="utf-8").count("\n## ")
    if nblocks > RECENT_LIMIT:
        issues.append(f"recent.md 有 {nblocks} 块，超过 {RECENT_LIMIT}")
    if st.get("turn", 0) < nblocks:
        issues.append("state.turn 小于 recent 块数，计数可能错乱")

    world_p = d / "world.md"
    if world_p.exists():
        wt = world_p.read_text(encoding="utf-8")
        for sec in ("## 一、铁律", "## 七、秘密分层", "## 八、基调与严酷度"):
            if sec not in wt:
                issues.append(f"world.md 缺章节：{sec}")

    open_n = sum(1 for t in st.get("threads", []) if t.get("status") == "open")

    if a.json:
        print(json.dumps({"turn": st.get("turn"), "open_threads": open_n,
                          "cast": len(cast), "issues": issues},
                         ensure_ascii=False, indent=2))
    else:
        print(f"轮次 {st.get('turn')} · 人物 {len(cast)} · 未结 {open_n}")
        if issues:
            print("发现问题：")
            for i in issues:
                print(f"  - {i}")
        else:
            print("检查通过。")

    return 1 if issues else 0


# ------------------------------------------------------------------ save / load
def cmd_save(a) -> int:
    d = _p(a.dir)
    st = load_state(d)
    cast = read_json(d / "cast.json").get("cast", []) if (d / "cast.json").exists() else []

    present = [c for c in cast if c.get("with_player") or c.get("id") in st["scene"].get("present", [])]
    recent_cast = [c for c in cast if int(c.get("last_seen", 0)) >= max(0, st["turn"] - 20)
                   and c.get("status") != "dead"]
    who = []
    for c in present or recent_cast:
        debt = c.get("debt") or {}
        who.append(f"{c['name']}（{debt.get('type','—')}·{c.get('status')}）")

    opens = [t for t in st.get("threads", []) if t.get("status") == "open"]
    lines = [
        f"# 恢复卡 · {st.get('title','')} · 第{st.get('turn')}轮",
        f"时间：{st.get('story_time','')} · {st['scene'].get('place','')}",
        f"在场：{'、'.join(who) if who else '无'}",
        f"焦点：{st['scene'].get('focus','')}",
        f"玩家：{st['player'].get('name','') or '（未命名）'}，{st['player'].get('condition','') or '无伤'}",
        "未结：" + ("；".join(f"{t['id']}{t['title']}（{t.get('pressure','')}）" for t in opens) or "无"),
        "已知：" + ("；".join(st["player"].get("known", [])[:6]) or "无"),
        "未知：" + ("；".join(st["player"].get("unknown", [])[:6]) or "无"),
    ]
    text = "\n".join(lines) + "\n"
    (d / "SAVE.md").write_text(text, encoding="utf-8")
    print(text)
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
    p.add_argument("--force", action="store_true"); p.set_defaults(func=cmd_init)

    p = sub.add_parser("turn"); p.add_argument("--dir", required=True)
    p.add_argument("--place"); p.add_argument("--time"); p.add_argument("--focus")
    p.add_argument("--present"); p.add_argument("--beats"); p.add_argument("--words")
    p.set_defaults(func=cmd_turn)

    p = sub.add_parser("thread"); p.add_argument("--dir", required=True)
    p.add_argument("--add"); p.add_argument("--pressure")
    p.add_argument("--close"); p.add_argument("--list", action="store_true")
    p.set_defaults(func=cmd_thread)

    p = sub.add_parser("check"); p.add_argument("--dir", required=True)
    p.add_argument("--json", action="store_true"); p.set_defaults(func=cmd_check)

    p = sub.add_parser("save"); p.add_argument("--dir", required=True); p.set_defaults(func=cmd_save)
    p = sub.add_parser("load"); p.add_argument("--dir", required=True); p.set_defaults(func=cmd_load)

    a = ap.parse_args(argv)
    try:
        return a.func(a)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"错误：{e}")
        return 2


if __name__ == "__main__":
    sys.exit(main())
