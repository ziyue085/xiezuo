# 写作 Skill · literary-craft

一个给 AI agent 用的中文文学写作与文学编辑 skill。
目标不是"去 AI 味"，是**让一个故事、一段经历、一篇文章值得读下去**。

> **状态**：v0.1.2，已完成两轮对照测试，**尚未通过外部人工验收**。未发布 Release。
> 仓库内容为待审核稿。

---

## 一句话安装（WorkBuddy）

```bash
d=$(mktemp -d) && { git clone --depth 1 https://github.com/ziyue085/xiezuo.git "$d/repo" 2>/dev/null || git clone --depth 1 git@github-ziyue085:ziyue085/xiezuo.git "$d/repo"; } && rm -rf ~/.workbuddy/skills/literary-craft && mkdir -p ~/.workbuddy/skills && cp -r "$d/repo/literary-craft" ~/.workbuddy/skills/ && rm -rf "$d"
```

装完重启会话，说"用 literary-craft 写个短篇"即可。

- 已在本机 Git Bash 实测：克隆成功、落盘 140 KB、**重复执行会覆盖旧版本**（不会产生 `literary-craft/literary-craft` 嵌套）。
- 任一克隆失败都会整条中断（不会拿旧目录凑合）。
- 没有 `github-ziyue085` 这个 SSH 别名的话，把第二段换成 `git@github.com:ziyue085/xiezuo.git`。

### 方式二：Skills CLI（适用于 Claude Code / Cursor 等）

```bash
npx skills add ziyue085/xiezuo --skill literary-craft -g -y
```

**实测状态（如实说明）**：

- 该 CLI 面向的是它支持的 agent（`--agent claude-code cursor` 等），**WorkBuddy 不在其中**，装了也不会进 `~/.workbuddy/skills`。
- 本机尝试两次均失败：HTTPS 克隆被网络阻断；改用 SSH 重写后仍认证失败。**因此这条命令没有在本机端到端验证过**，属于"理论可用、未验证"。
- 如果你在 Claude Code / Cursor 里用，它能工作；WorkBuddy 请用上面那一行。

Codex 用户：把 `literary-craft/` 目录放进自己的 skills 目录即可，无第三方依赖（只需要 Python 3.8+ 跑体检脚本）。

---

## 它解决什么

| 你遇到的 | skill 怎么处理 |
|---|---|
| 故事平淡，读不下去 | 用"落差"定位：没有落差、提前关闭、还是不兑现 |
| 人物扁平 | 四个字段：具体欲望、怕什么、信什么错的、怎么说话 |
| 细节多但没用 | 承重细节四条标准 + 替换测试 |
| 情绪直白 | 四条通道：命名 < 身体 < 动作偏差 < 注意力错位 |
| 对话没人味 | 每句台词都在做事；允许错位，但不给配额 |
| 为文学感牺牲故事 | 反公式化条款，含"设计感收尾"自查 |
| 历史写作编造引语 | 来源槽 / 粒度随来源 / 三类语法 / 证据台账 |
| 润色改过头 | 分级 + 保真七项 + 最小改动 + 越界自查 |

五种模式各有一套不合格线，不共用模板。**规则全部带适用条件**，没有"必须""一律"式的配额。

---

## 目录

```
.
├── literary-craft/            # 可安装的 skill
│   ├── SKILL.md               # 核心模型 + 路由（常驻，约 2.6k tokens）
│   ├── references/            # 7 份按需加载
│   ├── scripts/craft_lint.py  # 表层体检，只提示不打分
│   └── tests/                 # 30 项回归测试 + 两套场景
├── docs/
│   ├── RESEARCH.md            # 六部参考作品的机制分析 + 证据分级
│   ├── DESIGN.md              # 设计思路、取舍、适用边界
│   ├── EVALUATION.md          # 对照实验方法 + 统计口径
│   ├── RESULTS.md             # 第一轮结果（历史实验，已冻结）
│   ├── ROUND2.md              # 第二轮（另行预注册的测试集）
│   ├── ROUND1-DEFECTS.md      # 第一轮暴露的两个历史写作缺陷
│   └── REVIEW-RESPONSE.md     # 对 v0.1.1 审核意见的逐条处理
└── experiments/               # 全部原始产物：prompt、成品、盲评、指标
```

---

## 测试结果（两轮分开看）

**第一轮**（10 场景，4 位评审，含标签互换与苛刻提示）：B 32 / A 8；方向稳定 7/10。
**第二轮**（7 个另行预注册的场景，3 位评审）：B 16 / A 5；B 胜率 76%。

两轮共同指向的结论：

- **强项**：历史叙事（两轮均 4–0 / 3–0）、散文、人物与场景的具体性。
- **稳定失败**：幽默。第一轮 S06、第二轮 R05 都被判"把喜剧写成了温情"，第二轮 0–3。
- **短板**：约束遵守只有 57%→58%，接近抛硬币；skill 会让人物更"想写好"，反而更容易越界（写长、加戏、改文体）。
- **指标不可靠**：套话密度两轮均为 0（优势不来自"去 AI 味"）；情绪命名密度两轮方向相反。

**没有人类读者数据。** 评审都是模型。口径说明见 [`docs/EVALUATION.md`](docs/EVALUATION.md) 第 7 节。

---

## 复现

```bash
cd literary-craft && python -m unittest discover -s tests -v   # 30 tests
cd .. && python experiments/tools/analyze.py                   # 第一轮客观指标
python experiments/tools/aggregate.py                          # 第一轮盲评汇总
python experiments/tools/round2.py analyze                     # 第二轮客观指标
python experiments/tools/round2.py aggregate                   # 第二轮盲评汇总
```

---

## 许可

MIT。示例文本均为原创，未复制任何受版权保护的正文。
