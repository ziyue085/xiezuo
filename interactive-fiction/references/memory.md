# 长程记忆：五个文件、三条纪律、一种恢复

跑到三十轮以后，模型一定会忘。**"记住"不是能力，是文件。**

---

## 一、目录与文件

```
stories/<故事名>/
├── world.md      世界：规则、地理、势力、秘密分层   （很少改）
├── cast.json     人物：档案、关系、信息边界、位置
├── state.json    当前：场景、时间、未结线索、玩家状态
├── log.md        事件：只追加，一行一件
├── recent.md     近况：最近 8 轮的场所/动作/用语
└── SAVE.md       恢复卡：≤400 字，随时可重建
```

---

## 二、字段

### cast.json

```json
{
  "version": 1,
  "cast": [
    {
      "id": "zhou",
      "name": "周有德",
      "role": "都察院经历·顶头上司",
      "want": "今年考满升一级，别出事",
      "leverage": "掌握档案房的钥匙",
      "voice": "短句，公文腔，不说完整话",
      "knows": ["诏书副本存在", "司礼监在查"],
      "wrong_beliefs": ["以为是内阁放的"],
      "does_not_know": ["玩家见过原件"],
      "debt": {"type": "怕", "note": "玩家知道他私改过档"},
      "status": "active",
      "location": "都察院",
      "last_seen": 12,
      "with_player": false
    }
  ]
}
```

`status`：`active`（在场或可遇）／`away`（离场，记着什么时候回来）／`dead`。

**已死的人不能复活。** 死的时候在 `log.md` 写一行，`status` 改 `dead`，此后不得再出现在现场。

### state.json

```json
{
  "version": 1,
  "title": "诏书",
  "genre": "history",
  "tone": "冷硬",
  "severity": "标准",
  "turn": 24,
  "story_time": "隆庆六年三月十二，辰时",
  "scene": {
    "place": "都察院 档案房",
    "present": ["zhou"],
    "focus": "案上那份诏书副本"
  },
  "threads": [
    {"id": "t1", "title": "诏书副本从哪来", "status": "open",
     "since": 3, "pressure": "司礼监三日内来取"}
  ],
  "player": {
    "name": "",
    "known": ["诏书副本存在", "周有德私改过档"],
    "unknown": ["谁放的副本", "周有德与内阁的关系"],
    "assets": ["档案房钥匙副本"],
    "condition": "左臂轻伤"
  }
}
```

`threads[].status`：`open`（未结）／`closed`（已结）／`dormant`（暂时搁置，但要记着怎么唤醒）。

**已 closed 的事不能重演。** 这是长期一致性最常崩的地方。

### log.md

```markdown
# 事件

- [第03轮 · 三月十二] 玩家在案上发现诏书副本；周有德进门，看见他手里的东西。
- [第07轮 · 三月十三] 玩家把副本藏在靴筒；司礼监来人查房，没查到。
```

一行一件，只追加。**不写心理，不写评价。**

### recent.md

```markdown
# 最近 8 轮

## 第22轮
场所：档案房
动作：周有德锁门；玩家抄录日期
用语：锁、铜钥匙、声儿不对

## 第23轮
...
```

只留最近 8 轮，新的进，旧的出。用途只有一个：**防止同样的动作和句式再来一遍**。

### SAVE.md（恢复卡）

```markdown
# 恢复卡 · 诏书 · 第24轮
时间：隆庆六年三月十二 辰时 · 档案房
在场：周有德（怕玩家，正试探）
玩家：七品经历，左臂轻伤，手上有副本抄本
未结：①副本来源 ②司礼监三日内来取 ③周有德私改档的把柄
已知：副本存在；周改过档
未知：谁放的；周与内阁的关系
近三轮语感：短句，公文腔，物（钥匙、灯芯、靴筒）
下一步压力：门外有人上楼
```

**≤400 字。** 它替代不了全史，但能让人物、时间、未结的事、语感接得上。

---

## 三、三条纪律

1. **不每轮读全史。** 常规轮只读：`state.json` + 在场者的 `cast` 条目 + `recent.md`。`world.md` 只在进入新地点或涉及势力时读。
2. **不每轮重写世界。** `world.md` 极少动；`log.md` 只追加；`cast.json` 只改有变化的字段。
3. **有变化才写。** 没变化的回合，只更新 `turn` 和 `recent.md`。

### 更新决策树

```
这一轮发生了什么？
├─ 换了地方/换了时间        → state.scene, state.story_time
├─ 有人来了/走了            → cast[].with_player, scene.present
├─ 玩家知道了新东西        → player.known（从 unknown 移过来）
├─ 秘密被揭                 → threads 状态 + player.known
├─ 关系变了（欠/怕/图/亲）  → cast[].debt
├─ 有人死/重伤              → cast[].status, log.md
└─ 只是说了几句话          → 只更新 turn + recent.md
```

---

## 四、压缩后恢复（这是最关键的一环）

上下文被截断、换会话、/读档 时按这四步：

1. 读 `SAVE.md`（400 字，够重建现场）
2. 读 `state.json`（时间、场景、未结线索、玩家已知）
3. 读 `cast.json` 里 `status != dead` 且 `last_seen` 在近 20 轮内的条目
4. 读 `recent.md` 最后三块（只为语感，不为情节）

**恢复后的第一轮要做的**：不复述前情，直接以"下一步压力"那一条开头。

> 错：上次我们说到，你在档案房发现了诏书副本……
> 对：楼梯上有脚步声，不止一个人。

---

## 五、一致性检查（每 10 轮跑一次）

| # | 查什么 | 判据 |
|---|---|---|
| 1 | 年龄与时间 | 故事内过了多久，人该多大 |
| 2 | 地点可达 | 上一轮在通州，这一轮不能无解释在京城 |
| 3 | 死者不出场 | `status == dead` 的人不能说话 |
| 4 | 已结事件不重演 | `threads` 里 `closed` 的不能再开 |
| 5 | 信息边界 | NPC 不能知道 `does_not_know` 里的事 |
| 6 | 物品归属 | 送出去的东西不能还在玩家包里 |
| 7 | 伤势延续 | 上一轮断了手，这一轮不能提重物 |
| 8 | 承诺兑现 | `threads` 里的 deadline 有没有到期 |
| 9 | 玩家已知/未知 | 揭示过的要移出 `unknown` |
| 10 | 用语重复 | `recent.md` 里同一个动作出现三次以上 |

---

## 六、脚本

```bash
python scripts/if_state.py init --dir stories/诏书 --title 诏书 --genre history
python scripts/if_state.py turn --dir stories/诏书 --place 档案房 --beats "周有德锁门；玩家抄日期"
python scripts/if_state.py thread --dir stories/诏书 --add "副本从哪来" --pressure "三日内来取"
python scripts/if_state.py thread --dir stories/诏书 --close t1
python scripts/if_state.py check --dir stories/诏书
python scripts/if_state.py save --dir stories/诏书
python scripts/if_state.py load --dir stories/诏书
```

`check` 会跑上面十项里能自动判的部分（死者在场、悬空线索、轮次与 recent 长度、JSON 合法性）。

---

## 七、环境不支持写文件时

必须明确说一次：

> 「这一局不落盘。长局可能失真，我每 10 轮给你一段可复制的存档。」

然后每 10 轮输出一个 ``` 包裹的 `SAVE` 块，用户可粘贴回来继续。
