# literary-craft

中文文学写作与编辑 skill。给 WorkBuddy / Codex 这类 agent 用。v0.1.3。

它解决的不是"句子好不好看"，而是**读者为什么还要读下一段**。

---

## 安装（WorkBuddy，一行）

```bash
d=$(mktemp -d) && { git clone --depth 1 https://github.com/ziyue085/xiezuo.git "$d/repo" 2>/dev/null || git clone --depth 1 git@github-ziyue085:ziyue085/xiezuo.git "$d/repo"; } && bash "$d/repo/install.sh" "$d/repo"; rm -rf "$d"
```

装完重启会话，说"用 literary-craft 写个短篇"即可。

安装脚本：暂存 → 校验 → 备份旧版 → 替换，失败自动回滚。已实测四种情况：首装、重装（不嵌套）、校验失败（旧版保留）、备份后故障（回滚成功）。
没有 `github-ziyue085` 别名时，把第二段换成 `git@github.com:ziyue085/xiezuo.git`。

### Skills CLI（Claude Code / Cursor 等）

```bash
npx skills add ziyue085/xiezuo --skill literary-craft -g -y
```

如实说明：该 CLI 面向它支持的 agent，**WorkBuddy 不在其中**（不会装到 `~/.workbuddy/skills`）。本机两次尝试都因网络/认证失败，**未端到端验证**。

Codex 用户：把 `literary-craft/` 目录放进 skills 目录即可；只依赖 `SKILL.md` + Markdown + 一个 stdlib Python 脚本。

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

**渐进式加载**：常驻的只有 `SKILL.md`（约 2.6k tokens），按路由最多再读 2 份参考，峰值约 8k。

---

## 核心模型：落差

读者继续读，多数时候是因为有一个**尚未闭合的落差**，而且他知道这个落差值得等。

- 信息落差：有件事我还不知道
- 欲望落差：有人想要一样具体的东西，可能得不到
- 认知落差：我对这件事的理解，和文本要给的解释之间有空缺

判断一段该不该留，通常只需一句：**删掉它，读者会不会少等一件事？**

配套三条约束：细节最好承重、情绪有四条通道（命名 < 身体 < 动作偏差 < 注意力错位）、因果通常比顺序重要。

**但这些都不是配额。** 过渡段、气氛段、必要的信息交代，可以什么都不"制造"。

---

## 优先级

1. 用户明确要求（字数、视角、不许写什么、必须保留什么）
2. 事实与人物一致性
3. 阅读体验
4. 具体技巧

三条红线：不为吸引读者牺牲事实；不篡改原文（事实/视角/体裁）；不改变题材去迎合"更好看"。

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

能测：句长分布、段长分布、对话占比、情绪命名密度、套话密度、解释性标记、三连排比、"不是A而是B"、抽象名词密度、四字片段重复、时代错置词、英文直引号。

**不能**测：写得好不好、像不像人写的、结构有没有问题。

---

## 测试

```bash
python -m unittest discover -s tests -v      # 33 项回归测试
```

三轮对照实验见 `../docs/RESULTS.md`、`../docs/ROUND2.md`、`../docs/ROUND3.md`。

---

## 已知限制

- **幽默**：前两轮都判它"把喜剧写成温情"（第二轮 0–3）；第三轮两个新场景未复现（1 个 2–0、1 个 1–1），**不能算修好**。
- **事实准确性是短板**：第三轮事实与内部一致性 B 4–7 落后于裸写；写得更具体，也更容易出错。
- **约束遵守**：57%→58%，接近随机；会写长、加戏、在润色时改文体。
- 只管场景级，不管卷级；三章连续写作只做过一次 1–1 的探索性测试，无结论。
- 没有人类读者数据。所有评价来自模型评审。
- 文件里的数字（如"新增不超过一成半"）都是启发值，不是验收线。

---

## 目录

```
literary-craft/
├── SKILL.md
├── references/            7 份按需加载的参考
├── scripts/craft_lint.py  表层体检
├── tests/                 33 项回归测试 + 三套场景
├── README.md
└── CHANGELOG.md
```

设计思路见 `../docs/DESIGN.md`，研究依据见 `../docs/RESEARCH.md`，实验方法见 `../docs/EVALUATION.md`。

---

MIT License.
