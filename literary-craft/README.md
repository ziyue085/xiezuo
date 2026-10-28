# literary-craft

中文文学写作与编辑 skill。给 WorkBuddy / Codex 这类 agent 用。

它解决的不是"句子好不好看"，而是**读者为什么还要读下一段**。

---

## 安装（一行）

```bash
git clone --depth 1 https://github.com/ziyue085/xiezuo.git /tmp/xiezuo && mkdir -p ~/.workbuddy/skills && cp -r /tmp/xiezuo/literary-craft ~/.workbuddy/skills/ && rm -rf /tmp/xiezuo
```

装完重启会话，说一句"用 literary-craft 写个短篇"即可触发。

> Codex 用户：把 `literary-craft/` 整个目录放到你的 skills 目录（如 `~/.codex/skills/`）。本包只依赖 `SKILL.md` + Markdown + 一个 stdlib Python 脚本，无第三方依赖。

---

## 它做什么

| 模式 | 触发 | 加载 |
|---|---|---|
| **A 小说** | 写故事、小说、片段、续写 | `references/fiction.md` |
| **B 历史叙事** | 写历史、写古人、历史小说 | `references/history.md` |
| **C 散文** | 写散文、随笔、游记 | `references/essay.md` |
| **D 润色** | 改一段已有的文字 | `references/revise.md` |
| **E 文学编辑** | 评一篇稿子、给修改意见 | `references/edit.md` |

语言层面的具体毛病 → `references/anti-patterns.md`（15 组病灶图鉴）
节奏与句式 → `references/rhythm.md`

**渐进式加载**：常驻的只有 `SKILL.md`（约 2.5k tokens），按路由最多再读 2 份参考，峰值约 8k。

---

## 核心模型：落差

读者继续读，是因为有一个**尚未闭合的落差**，而且他知道这个落差值得等。

- 信息落差：有件事我还不知道
- 欲望落差：有人想要一样具体的东西，可能得不到
- 认知落差：我对这件事的理解，和文本要给的解释之间有空缺

判断一段该不该留，只需一句：**删掉它，读者会不会少等一件事？**

配套三条硬约束：细节必须承重、情绪有四条通道（命名 < 身体 < 动作偏差 < 注意力错位）、因果不是顺序（场景结束必须有状态变化）。

---

## 它明确不做的事

- 不模仿任何特定作家的文风（六部参考作品的风格互相冲突）
- 不把"展示而非讲述""多用短句""少用形容词"当绝对规则
- 不输出创作过程（除非你要看）
- 不覆盖公文、论文、商业文案、诗歌格律
- 不承诺写到可发表水平——它抬下限，抬不高上限

---

## 体检脚本

只做提示，不打分。命中不等于差，未命中不等于好。

```bash
python scripts/craft_lint.py --file draft.txt              # 人类可读
python scripts/craft_lint.py --file draft.txt --json       # 机器可读
python scripts/craft_lint.py --file draft.txt --mode fiction
python scripts/craft_lint.py --file draft.txt --mode history --era ancient
```

退出码：`0` 无提示 / `1` 有提示（需人工判断）/ `2` 参数或文件错误。

它能测：句长分布、段长分布、对话占比、情绪命名密度、套话密度、解释性标记、三连排比、"不是A而是B"、抽象名词密度、四字片段重复、时代错置词。

它**不能**测：写得好不好、像不像人写的、结构有没有问题。

---

## 测试

```bash
cd literary-craft
python -m unittest discover -s tests -v      # 27 项回归测试
```

10 个原创场景与对照实验结果见 `../docs/RESULTS.md`。

---

## 已知限制

- 会倾向于"设计过的克制"：把冲突推向沉默、结尾用回环或定格。这在离别、幽默、现实主义题材上会失分（实测 3 个场景打成 2–2）。
- 约束遵守不稳定：实测"题材与约束契合"维度只有 57% 胜率，有写长、加戏的倾向。
- 只管场景级，不管卷级；只测过 1000–1800 字的短篇。
- 没有人类读者数据。所有评价来自模型评审。

---

## 目录

```
literary-craft/
├── SKILL.md
├── references/            7 份按需加载的参考
├── scripts/craft_lint.py  表层体检
├── tests/                 回归测试 + 10 个场景
├── README.md
└── CHANGELOG.md
```

设计思路见 `../docs/DESIGN.md`，研究依据见 `../docs/RESEARCH.md`，实验方法见 `../docs/EVALUATION.md`。

---

MIT License.
