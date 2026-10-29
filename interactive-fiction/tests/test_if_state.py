#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""if_state.py 回归测试：只测"状态文件能不能正确读写与校验"，不测故事好坏。"""

from __future__ import annotations

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


class TestState(unittest.TestCase):

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name) / "story"

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _init(self) -> None:
        self.assertEqual(run("init", "--dir", str(self.dir), "--title", "测试"), 0)

    def _add_cast(self, cid: str = "a", status: str = "active") -> None:
        p = self.dir / "cast.json"
        data = json.loads(p.read_text(encoding="utf-8"))
        data["cast"].append({
            "id": cid, "name": "甲", "role": "测试角色", "want": "活着",
            "voice": "短句", "knows": [], "does_not_know": [],
            "status": status, "last_seen": 1, "with_player": True,
        })
        p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def test_init_creates_files(self) -> None:
        self._init()
        for f in ("world.md", "cast.json", "state.json", "log.md", "recent.md"):
            self.assertTrue((self.dir / f).exists(), f)

    def test_turn_increments_and_rolls(self) -> None:
        self._init()
        for i in range(1, 12):
            self.assertEqual(run("turn", "--dir", str(self.dir), "--beats", f"动作{i}"), 0)
        s = json.loads((self.dir / "state.json").read_text(encoding="utf-8"))
        self.assertEqual(s["turn"], 11)
        txt = (self.dir / "recent.md").read_text(encoding="utf-8")
        self.assertEqual(txt.count("\n## "), st.RECENT_LIMIT)
        self.assertNotIn("第1轮", txt)
        self.assertIn("第11轮", txt)

    def test_thread_add_and_close(self) -> None:
        self._init()
        self.assertEqual(run("thread", "--dir", str(self.dir), "--add", "找证据"), 0)
        s = json.loads((self.dir / "state.json").read_text(encoding="utf-8"))
        self.assertEqual(s["threads"][0]["status"], "open")
        self.assertEqual(run("thread", "--dir", str(self.dir), "--close", "t1"), 0)
        s = json.loads((self.dir / "state.json").read_text(encoding="utf-8"))
        self.assertEqual(s["threads"][0]["status"], "closed")

    def test_check_flags_dead_present(self) -> None:
        self._init()
        self._add_cast("deadman", status="dead")
        s = json.loads((self.dir / "state.json").read_text(encoding="utf-8"))
        s["scene"]["present"] = ["deadman"]
        (self.dir / "state.json").write_text(
            json.dumps(s, ensure_ascii=False), encoding="utf-8")
        self.assertEqual(run("check", "--dir", str(self.dir)), 1)

    def test_check_clean(self) -> None:
        self._init()
        self._add_cast("a")
        self.assertEqual(run("check", "--dir", str(self.dir)), 0)

    def test_save_and_load(self) -> None:
        self._init()
        self._add_cast("a")
        run("turn", "--dir", str(self.dir), "--place", "档案房", "--beats", "锁门")
        self.assertEqual(run("save", "--dir", str(self.dir)), 0)
        text = (self.dir / "SAVE.md").read_text(encoding="utf-8")
        self.assertIn("档案房", text)
        self.assertIn("第1轮", text)
        self.assertLessEqual(len(text), 500)
        self.assertEqual(run("load", "--dir", str(self.dir)), 0)

    def test_init_refuses_existing(self) -> None:
        self._init()
        self.assertEqual(run("init", "--dir", str(self.dir), "--title", "再来"), 2)


if __name__ == "__main__":
    unittest.main()
