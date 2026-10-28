# 写作 Skill · literary-craft

一个给 AI agent 用的中文文学写作与文学编辑 skill。
目标不是"去 AI 味"，是**让一个故事、一段经历、一篇文章值得读下去**。

> **状态**：v0.1.1，已完成内部 A/B 对照测试，**尚未经过外部人工审核**。
> 未发布 Release。仓库内容为待审核稿。

---

## 一句话安装

```bash
git clone --depth 1 https://github.com/ziyue085/xiezuo.git /tmp/xiezuo && mkdir -p ~/.workbuddy/skills && cp -r /tmp/xiezuo/literary-craft ~/.workbuddy/skills/ && rm -rf /tmp/xiezuo
```

装完重启会话，说"用 literary-craft 写个短篇"即可。Codex 用户把 `literary-craft/` 放进自己的 skills 目录即可，无第三方依赖。

---

## 它解决什么

| 你遇到的 | skill 怎么处理 |
|---|---|
| 故事平淡，读不下去 | 用"落差"定位：是没有落差、提前关闭、还是不兑现 |
| 人物扁平 | 四个字段定人物：具体欲望、怕什么、信什么错的、怎么说话 |
| 细节多但没用 | "承重细节"四条标准 + 替换测试（换个同类细节，文本变了吗） |
| 情绪直白 | 四条通道排序：命名 < 身体 < 动作偏差 < 注意力错位 |
| 对话没人味 | 每句台词都在做事；要求 30%–50% 的错位 |
| 为文学感牺牲故事 | 反公式化条款：五条反向操作，含"设计感收尾"自查 |
| 历史写作编造引语 | 三层标注（史/推/构）+ 五条硬禁令 + 时代校验九项 |
| 润色改过头 | 分级（L0/L1/L2）+ 保真七项 + 最小改动原则 |

五种模式各有一套不合格线，不共用一套模板。

---

## 目录

```
.
├── literary-craft/          # 可安装的 skill
│   ├── SKILL.md             # 核心模型 + 路由（常驻，约 2.5k tokens）
│   ├── references/          # 7 份按需加载（小说/历史/散文/润色/编辑/病灶/节奏）
│   ├── scripts/craft_lint.py# 表层体检，只提示不打分
│   └── tests/               # 27 项回归测试 + 10 个原创场景
├── docs/
│   ├── RESEARCH.md          # 六部参考作品的机制分析 + 证据分级
│   ├── DESIGN.md            # 设计思路、取舍、适用边界
│   ├── EVALUATION.md        # 对照实验与评价方法
│   └── RESULTS.md           # 测试结果、失败项、无证据的结论
└── experiments/             # 全部原始产物：prompt、成品、盲评、指标
```

---

## 测试结果（摘要）

10 个原创场景（人物离别／市井／历史冲突／历史事件／权谋对话／幽默反转／现实主义／散文／两篇润色），同模型、同 prompt，A 裸写 vs B 启用 skill，匿名后 4 位评审盲评（其中 2 位用**标签互换**的材料，控制位置偏差）。

- 40 次判断：**B 32 / A 8**
- 方向稳定（≥3/4 评审同向）：**7/10 场景**
- 最强：人物鲜活度 92%、场景可感度 88%
- 最弱：**题材与约束契合 57%**（接近随机，B 有写长、加戏的倾向）
- 3 个场景打成 2–2：人物离别、幽默反转、现实主义——**B 在这三类上优势消失甚至反转**
- 客观指标：套话密度两组都是 0，**B 的优势不来自"去 AI 味"**；只有句长 CV（0.59→0.67）和情绪命名密度（−42%）有可测差异

**没有人类读者数据，评审也是模型。** 详见 [`docs/RESULTS.md`](docs/RESULTS.md) 第 6 节"哪些结论没有足够证据"。

---

## 复现

```bash
cd literary-craft && python -m unittest discover -s tests -v   # 27 tests
cd .. && python experiments/tools/analyze.py                   # 客观指标
python experiments/tools/aggregate.py                          # 盲评汇总
```

---

## 许可

MIT。示例文本均为原创，未复制任何受版权保护的正文。
