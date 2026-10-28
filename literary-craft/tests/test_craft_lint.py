#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""craft_lint 回归测试

原则：只测"能不能稳定识别"，不测"文本好不好"。
每个用例构造一段会触发/不触发某项检查的最小文本。
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import craft_lint as cl  # noqa: E402

SCRIPT = ROOT / "scripts" / "craft_lint.py"


def codes(text: str, mode: str = "generic", era: str = "") -> list[str]:
    return [f["code"] for f in cl.analyze(text, mode=mode, era=era)["flags"]]


class TestParsing(unittest.TestCase):
    def test_cjk_len_ignores_punct_and_latin(self):
        self.assertEqual(cl.cjk_len("他说：OK，走了。"), 4)

    def test_paragraphs_blank_line(self):
        paras = cl.split_paragraphs("第一段。\n\n第二段。\n\n第三段。")
        self.assertEqual(len(paras), 3)

    def test_paragraphs_single_newline(self):
        paras = cl.split_paragraphs("第一段。\n第二段。\n第三段。")
        self.assertEqual(len(paras), 3)

    def test_paragraph_soft_wrap_merged(self):
        paras = cl.split_paragraphs("第一段前半\n接着写。\n\n第二段。")
        self.assertEqual(paras[0], "第一段前半接着写。")

    def test_split_sentences_keeps_quote(self):
        sents = cl.split_sentences("他说：「走吧。」她没动。")
        self.assertEqual(len(sents), 2)

    def test_dialogue_chars_corner_quotes(self):
        n = cl.dialogue_chars("「今天走吗。」他说。「不走。」")
        self.assertEqual(n, 6)

    def test_dialogue_chars_curly_quotes(self):
        n = cl.dialogue_chars("“今天走吗。”他说。“不走。”")
        self.assertEqual(n, 6)

    def test_percentile_edges(self):
        self.assertEqual(cl.percentile([1, 2, 3], 0.0), 1)
        self.assertEqual(cl.percentile([1, 2, 3], 1.0), 3)

    def test_cv_zero_for_identical(self):
        self.assertAlmostEqual(cl.cv([10.0, 10.0, 10.0]), 0.0)


class TestFlags(unittest.TestCase):
    def test_clean_text_has_no_flags(self):
        text = (
            "他推开门。屋里没开灯，桌上一只碗，碗里剩了半碗饭。\n"
            "「回来了。」他妈在里屋说。\n"
            "「嗯。」\n"
            "他把碗端到灶台上，揭开锅盖，锅里是空的。他站着看了一会儿，"
            "把碗放回去，从口袋里摸出二十块钱压在碗底下。\n"
            "里屋的电视声音很大。他站到门口，又退回来，把钱抽走十块，"
            "剩下十块压回原处。\n"
            "外面下雨了。他把外套的帽子拉起来，走进雨里。"
        )
        self.assertEqual(codes(text), [])

    def test_emotion_named(self):
        text = ("她感到一阵莫名的悲伤，心里很难受。" * 4) + "他走了。"
        self.assertIn("EMOTION_NAMED", codes(text))

    def test_body_reaction_suppresses_emotion_flag(self):
        text = ("她感到一阵悲伤，喉咙发紧，手心出汗。" * 4) + "他走了。"
        self.assertNotIn("EMOTION_NAMED", codes(text))

    def test_cliche(self):
        text = "仿佛过了很久。他不禁想起那天，一丝寒意涌上来。" * 3
        self.assertIn("CLICHE", codes(text))

    def test_not_a_but_b(self):
        text = "这不是告别，而是一次放逐。那不是愤怒，而是恐惧。" * 2
        self.assertIn("NOT_A_BUT_B", codes(text))

    def test_parallel3(self):
        text = "是母亲的期盼，是故乡的召唤，是生命的归途。" * 3
        self.assertIn("PARALLEL3", codes(text))

    def test_dash_requires_absolute_count(self):
        # 短文本里一个破折号密度很高，但不应触发
        short = "他走了——带着秘密。外面在下雨，他把帽子拉起来，走进雨里。"
        self.assertNotIn("DASH_HEAVY", codes(short))

    def test_dash_heavy_when_repeated(self):
        text = "他走了——带着秘密。" * 4
        self.assertIn("DASH_HEAVY", codes(text))

    def test_over_explain(self):
        text = ("他把碗放下。这说明他已经下定决心。这也意味着他不会再回来。" * 3)
        self.assertIn("OVER_EXPLAIN", codes(text))

    def test_rhythm_flat(self):
        text = "他在路上走了很久，看见路边的树和远处的房子，心里想着昨天的事情。" * 16
        self.assertIn("RHYTHM_FLAT", codes(text))

    def test_repeat_4gram(self):
        text = "他把碗放在桌子上。" * 8
        self.assertIn("REPEAT", codes(text))

    def test_abstract_heavy(self):
        text = ("时代的命运与个人的价值，构成了精神的意义与灵魂的本质。" * 4)
        self.assertIn("ABSTRACT_HEAVY", codes(text))

    def test_fiction_no_dialogue(self):
        text = "他在路上走了很久，看见路边的树和远处的房子，心里想着昨天的事情。" * 12
        self.assertIn("NO_DIALOGUE", codes(text, mode="fiction"))

    def test_anachronism_only_in_ancient(self):
        text = "他召集干部开会，布置下一阶段的工作任务，要求提高效率。" * 4
        self.assertIn("ANACHRONISM", codes(text, mode="history", era="ancient"))
        self.assertNotIn("ANACHRONISM", codes(text, mode="history"))


class TestCli(unittest.TestCase):
    def _run(self, text: str, *args: str) -> subprocess.CompletedProcess:
        with tempfile.NamedTemporaryFile("w", suffix=".txt", encoding="utf-8",
                                         delete=False) as fh:
            fh.write(text)
            path = fh.name
        try:
            return subprocess.run(
                [sys.executable, str(SCRIPT), "--file", path, *args],
                capture_output=True, text=True, encoding="utf-8",
            )
        finally:
            Path(path).unlink(missing_ok=True)

    def test_exit_2_when_too_short(self):
        r = self._run("太短。")
        self.assertEqual(r.returncode, 2)

    def test_exit_1_when_flags(self):
        r = self._run("她感到一阵莫名的悲伤，心里很难受。" * 5)
        self.assertEqual(r.returncode, 1)

    def test_json_output_is_valid(self):
        r = self._run("他推开门。屋里没开灯，桌上有一只碗，碗里剩了半碗饭。" * 4, "--json")
        data = json.loads(r.stdout)
        self.assertIn("metrics", data)
        self.assertIn("flags", data)

    def test_missing_file_exit_2(self):
        r = subprocess.run(
            [sys.executable, str(SCRIPT), "--file", "no_such_file_xyz.txt"],
            capture_output=True, text=True,
        )
        self.assertEqual(r.returncode, 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
