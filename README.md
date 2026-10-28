# 写作 Skill · literary-craft

一个给 AI agent 用的中文文学写作与文学编辑 skill。
目标不是"去 AI 味"，是**让一个故事、一段经历、一篇文章值得读下去**。

> **状态**：v0.1.3，已完成三轮对照测试，**尚未通过外部文学质量验收**。未发布 Release。

---

## 一句话安装（WorkBuddy）

```bash
d=$(mktemp -d) && { git clone --depth 1 https://github.com/ziyue085/xiezuo.git "$d/repo" 2>/dev/null || git clone --depth 1 git@github-ziyue085:ziyue085/xiezuo.git "$d/repo"; } && bash "$d/repo/install.sh" "$d/repo"; rm -rf "$d"
```

装完重启会话，说"用 literary-craft 写个短篇"即可。

安装脚本做四件事：**暂存 → 校验 → 备份旧版 → 替换**；任一步失败自动回滚，原有安装保留。

已实测四种情况：

| 情况 | 结果 |
|---|---|
| 首次安装 | ✓ 落盘 140 KB |
| 重复安装 | ✓ 覆盖旧版，不产生 `literary-craft/literary-craft` 嵌套 |
| 新版本校验失败（伪造仓库） | ✓ 退出码 1，旧版完好 |
| 备份后强制失败（故障注入） | ✓ 回滚，旧版恢复，无残留备份目录 |

没有 `github-ziyue085` 别名时，把第二段换成 `git@github.com:ziyue085/xiezuo.git`。

### 方式二：Skills CLI（Claude Code / Cursor 等）

```bash
npx skills add ziyue085/xiezuo --skill literary-craft -g -y
```

如实说明：该 CLI 面向它支持的 agent，**WorkBuddy 不在其中**；本机两次尝试都因网络/认证失败，**未端到端验证**。

---

## 它解决什么

| 你遇到的 | skill 怎么处理 |
|---|---|
| 故事平淡 | 用"落差"定位：没有落差、提前关闭、还是不兑现 |
| 人物扁平 | 四个字段：具体欲望、怕什么、信什么错的、怎么说话 |
| 细节多但没用 | 承重细节四条标准 + 替换测试 |
| 情绪直白 | 四条通道：命名 < 身体 < 动作偏差 < 注意力错位 |
| 历史写作编造引语 | 来源槽 / 核实状态 / 粒度随来源 / 制度断言看执行 |
| 润色改过头 | 先抄事实清单，逐条对，多一条删掉 |
| 喜剧写成温情 | 先定作品目标，让人物按利益行动 |

五种模式各有一套不合格线。**规则全部带适用条件**，没有"必须""一律"式配额。

---

## 测试结果（三轮分开看，不合并）

| 轮次 | 场景 | 结果 | 主要发现 |
|---|---|---|---|
| 第一轮 | 10（4 位评审） | B 32 / A 8 | 人物、场景优势明显；幽默失败 |
| 第二轮 | 7（3 位评审） | B 16 / A 5 | 幽默复现失败（0–3）；约束遵守 58% |
| 第三轮 | 6（2 位评审） | **B 6 / A 6** | 语言 B 优（9–3），**事实 A 优（7–4）** |

结论：

- **强项**：历史叙事的材料纪律、散文、语言自然度。
- **稳定短板**：事实与内部一致性——第三轮 B 组反而落后；写得更具体，也更容易出错。
- **幽默**：两轮失败、第三轮未复现（2 个场景，1 个 2–0、1 个 1–1），**不能声称修好**。
- **没有人类读者数据**，评审是同一模型的两个隔离实例。

口径见 [`docs/EVALUATION.md`](docs/EVALUATION.md) §7。

---

## 目录

```
.
├── literary-craft/            # 可安装的 skill
│   ├── SKILL.md               # 核心模型 + 路由（常驻，约 2.6k tokens）
│   ├── references/            # 7 份按需加载
│   ├── scripts/craft_lint.py  # 表层体检，只提示不打分
│   └── tests/                 # 33 项回归测试 + 三套场景
├── install.sh                 # 暂存/校验/备份/替换/回滚
├── docs/
│   ├── RESEARCH.md            # 六部参考作品的机制分析 + 证据分级
│   ├── DESIGN.md              # 设计思路、取舍、边界
│   ├── EVALUATION.md          # 方法与统计口径
│   ├── RESULTS.md             # 第一轮（已冻结）
│   ├── ROUND2.md              # 第二轮
│   ├── ROUND3.md              # 第三轮（含 R04 史实核查结论）
│   ├── ROUND1-DEFECTS.md      # 第一轮的两个历史写作缺陷
│   └── REVIEW-RESPONSE.md     # 对两轮审核意见的逐条处理
└── experiments/               # 全部原始产物：prompt、成品、盲评、指标
```

---

## 复现

```bash
cd literary-craft && python -m unittest discover -s tests -v   # 33 tests
cd .. && python experiments/tools/analyze.py                   # 第一轮指标
python experiments/tools/round2.py analyze                     # 第二轮
python experiments/tools/round3.py check                       # 第三轮硬约束
python experiments/tools/round3.py aggregate                   # 第三轮盲评
```

---

## 许可

MIT。示例文本均为原创，未复制任何受版权保护的正文。
