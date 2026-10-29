#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""if_state.py 回归测试：只测"状态文件能不能正确读写与校验"，不测故事好坏。

覆盖 v0.1.1 新增的六类校验：到期未处理、物品双属、年号越界、事件落 log、
存档长度上限、在场一致性。
"""

from __future__ import annotations

import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import if_state as st  # noqa: E402


def run(*args: str) -> int:
    return st.main(list(args))


def run_json(*args: str) -> dict:
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        st.main(list(args))
    return json.loads(buf.getvalue())


class Base(unittest.TestCase):

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name) / "story"

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _init(self, era: str = "隆庆", year: int = 6) -> None:
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(run("init", "--dir", str(self.dir), "--title", "测试",
                                 "--era", era, "--year", str(year)), 0)

    def _cast(self, cid: str = "a", status: str = "active", major: bool = True) -> None:
        p = self.dir / "cast.json"
        data = json.loads(p.read_text(encoding="utf-8"))
        data["cast"].append({
            "id": cid, "name": cid, "role": "测试", "want": "活着", "voice": "短句",
            "knows": [], "does_not_know": [], "status": status,
            "last_seen": 1, "with_player": status != "dead", "major": major,
        })
        p.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    def _state(self) -> dict:
        return json.loads((self.dir / "state.json").read_text(encoding="utf-8"))

    def _patch(self, **kw) -> None:
        s = self._state()
        s.update(kw)
        (self.dir / "state.json").write_text(json.dumps(s, ensure_ascii=False), encoding="utf-8")


class TestBasic(Base):

    def test_init_creates_files(self) -> None:
        self._init()
        for f in ("world.md", "cast.json", "state.json", "log.md", "recent.md"):
            self.assertTrue((self.dir / f).exists(), f)
        self.assertIn("隆庆", (self.dir / "state.json").read_text(encoding="utf-8"))

    def test_turn_increments_and_rolls(self) -> None:
        self._init()
        for i in range(1, 12):
            with contextlib.redirect_stdout(io.StringIO()):
                run("turn", "--dir", str(self.dir), "--beats", f"动作{i}")
        self.assertEqual(self._state()["turn"], 11)
        txt = (self.dir / "recent.md").read_text(encoding="utf-8")
        self.assertEqual(txt.count("\n## "), st.RECENT_LIMIT)
        self.assertNotIn("第1轮", txt)

    def test_turn_writes_log(self) -> None:
        self._init()
        with contextlib.redirect_stdout(io.StringIO()):
            run("turn", "--dir", str(self.dir), "--event", "玩家拿到副本")
        log = (self.dir / "log.md").read_text(encoding="utf-8")
        self.assertIn("玩家拿到副本", log)
        self.assertIn("隆庆", log)


class TestThreads(Base):

    def test_thread_requires_fields(self) -> None:
        self._init()
        self._cast("a")
        with contextlib.redirect_stdout(io.StringIO()):
            run("thread", "--dir", str(self.dir), "--add", "查副本")
        out = run_json("check", "--dir", str(self.dir), "--json")
        self.assertTrue(any("缺 owner" in w for w in out["warnings"]))
        self.assertEqual(out["errors"], [])

    def test_overdue_detected(self) -> None:
        self._init()
        self._cast("a")
        with contextlib.redirect_stdout(io.StringIO()):
            run("thread", "--dir", str(self.dir), "--add", "交副本", "--owner", "a",
                "--deadline-days", "2", "--trigger", "司礼监来取", "--overdue", "副本被收缴")
        with contextlib.redirect_stdout(io.StringIO()):
            run("turn", "--dir", str(self.dir), "--day-step", "3")
        out = run_json("check", "--dir", str(self.dir), "--json")
        self.assertTrue(any("到期未处理" in e for e in out["errors"]))

    def test_overdue_not_triggered_before_deadline(self) -> None:
        self._init()
        self._cast("a")
        with contextlib.redirect_stdout(io.StringIO()):
            run("thread", "--dir", str(self.dir), "--add", "交副本", "--owner", "a",
                "--deadline-days", "5", "--trigger", "x", "--overdue", "y")
        out = run_json("check", "--dir", str(self.dir), "--json")
        self.assertFalse(any("到期未处理" in e for e in out["errors"]))


class TestOwnership(Base):

    def test_holds_lost_overlap(self) -> None:
        self._init()
        self._cast("a")
        s = self._state()
        s["player"]["holds"] = ["副本", "钥匙"]
        s["player"]["lost"] = ["副本"]
        (self.dir / "state.json").write_text(json.dumps(s, ensure_ascii=False), encoding="utf-8")
        out = run_json("check", "--dir", str(self.dir), "--json")
        self.assertTrue(any("同时在持有与已失去" in e for e in out["errors"]))


class TestTime(Base):

    def test_era_overflow_rejected(self) -> None:
        self._init()
        rc = run("time", "--dir", str(self.dir), "--era", "隆庆", "--year", "7",
                 "--month", "1", "--day", "1")
        self.assertEqual(rc, 2)

    def test_wrong_next_era_rejected(self) -> None:
        self._init()
        rc = run("time", "--dir", str(self.dir), "--era", "天启", "--year", "1",
                 "--month", "1", "--day", "1")
        self.assertEqual(rc, 2)

    def test_correct_era_change(self) -> None:
        self._init()
        rc = run("time", "--dir", str(self.dir), "--era", "万历", "--year", "1",
                 "--month", "1", "--day", "4")
        self.assertEqual(rc, 0)
        self.assertIn("万历元年", self._state()["story_time"])

    def test_month_overflow(self) -> None:
        self._init()
        rc = run("time", "--dir", str(self.dir), "--month", "13")
        self.assertEqual(rc, 2)


class TestPresence(Base):

    def test_dead_in_present(self) -> None:
        self._init()
        self._cast("deadman", status="dead")
        self._patch(scene={"place": "x", "present": ["deadman"], "focus": ""})
        out = run_json("check", "--dir", str(self.dir), "--json")
        self.assertTrue(any("死者仍在场" in e for e in out["errors"]))

    def test_missing_cast_id(self) -> None:
        self._init()
        self._patch(scene={"place": "x", "present": ["ghost"], "focus": ""})
        out = run_json("check", "--dir", str(self.dir), "--json")
        self.assertTrue(any("不在 cast.json" in e for e in out["errors"]))


class TestSave(Base):

    def test_save_contains_voice_and_relation(self) -> None:
        self._init()
        self._cast("a")
        with contextlib.redirect_stdout(io.StringIO()):
            run("turn", "--dir", str(self.dir), "--place", "档案房")
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            run("save", "--dir", str(self.dir))
        text = (self.dir / "SAVE.md").read_text(encoding="utf-8")
        self.assertIn("短句", text)
        self.assertIn("档案房", text)

    def test_save_length_limit(self) -> None:
        self._init()
        self._cast("a")
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            run("save", "--dir", str(self.dir), "--max", "80")
        text = (self.dir / "SAVE.md").read_text(encoding="utf-8")
        self.assertLessEqual(len(text), 80 + 30)
        self.assertIn("已裁剪", text)


class TestCalendarSync(Base):
    """v0.1.2 修的三件事：time 与 day_index 同步、跨年自动改元、--year 绕不过校验。"""

    def _time(self, *args: str) -> int:
        with contextlib.redirect_stdout(io.StringIO()):
            return run("time", "--dir", str(self.dir), *args)

    def _turn(self, *args: str) -> int:
        with contextlib.redirect_stdout(io.StringIO()):
            return run("turn", "--dir", str(self.dir), *args)

    def _check(self) -> dict:
        return run_json("check", "--dir", str(self.dir), "--json")

    def test_time_moves_day_index(self) -> None:
        self._init()
        self.assertEqual(self._time("--month", "3", "--day", "12"), 0)
        cal = self._state()["calendar"]
        self.assertEqual(cal["day_index"], 72)          # 1 月 1 日算第 1 天，3 月 12 日是第 72 天
        self.assertEqual(self._check()["errors"], [])

    def test_time_keeps_month_when_only_day_given(self) -> None:
        self._init()
        self._time("--month", "3", "--day", "12")
        self._time("--day", "15")
        cal = self._state()["calendar"]
        self.assertEqual((cal["month"], cal["day"]), (3, 15))

    def test_year_alone_cannot_bypass_era_limit(self) -> None:
        self._init()
        self.assertEqual(self._time("--year", "7"), 2)
        cal = self._state()["calendar"]
        self.assertEqual((cal["era"], cal["year"]), ("隆庆", 6))

    def test_turn_cross_year_auto_changes_era(self) -> None:
        self._init()
        self._time("--month", "12", "--day", "29")
        self._turn("--day-step", "2")
        st = self._state()
        cal = st["calendar"]
        self.assertEqual((cal["era"], cal["year"], cal["month"], cal["day"]),
                         ("万历", 1, 1, 1))
        self.assertIn("万历元年", st["story_time"])
        self.assertNotIn("隆庆七", st["story_time"])

    def test_era_change_requires_first_year(self) -> None:
        self._init()
        self._time("--month", "12", "--day", "30")
        self.assertEqual(self._time("--era", "万历", "--year", "2"), 2)

    def test_era_change_blocked_before_last_year(self) -> None:
        self._init(year=4)
        self.assertEqual(self._time("--era", "万历", "--year", "1"), 2)

    def test_negative_day_step_rejected(self) -> None:
        self._init()
        self.assertEqual(self._turn("--day-step", "-1"), 2)

    def test_check_flags_day_index_drift_and_time_fixes_it(self) -> None:
        self._init()
        self._time("--month", "3", "--day", "12")
        s = self._state()
        s["calendar"]["day_index"] = 999
        (self.dir / "state.json").write_text(json.dumps(s, ensure_ascii=False), encoding="utf-8")
        self.assertTrue(any("不同步" in e for e in self._check()["errors"]))
        self._time("--month", "3", "--day", "12")      # 同一日期重设一次即对齐
        self.assertEqual(self._state()["calendar"]["day_index"], 72)
        self.assertEqual(self._check()["errors"], [])


class TestSaveClosed(Base):
    """已结的事必须进恢复卡，否则新会话会把它当成未决线重提。"""

    def test_closed_thread_in_save(self) -> None:
        self._init()
        self._cast("a")
        with contextlib.redirect_stdout(io.StringIO()):
            run("thread", "--dir", str(self.dir), "--add", "取件期限", "--owner", "a",
                "--deadline-days", "3", "--trigger", "司礼监来人", "--overdue", "副本被收缴")
            run("turn", "--dir", str(self.dir), "--day-step", "5")
            run("thread", "--dir", str(self.dir), "--close", "t1", "--note", "原件已交出")
        with contextlib.redirect_stdout(io.StringIO()):
            run("save", "--dir", str(self.dir))
        text = (self.dir / "SAVE.md").read_text(encoding="utf-8")
        self.assertIn("已结：", text)
        self.assertIn("原件已交出", text)
        self.assertIn("未结：无", text)
        self.assertNotIn("取件期限（a·第", text)


if __name__ == "__main__":
    unittest.main()
