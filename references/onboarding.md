# 给一个业务建它自己的 skill（Agent 照这个做）

业务同学把手上的表全塞过来、讲清自己的流程，**Agent 建出这个业务专属的 skill**：一份完整能跑的工厂，事实来自他们的资料，流程按他们说的来。这份文档是 Agent 的操作步骤；业务同学不用看配置字段。

**不改这个模板仓库本身**。每个业务建在自己的新目录里（默认 `~/skills/<key>-daily-batch`，或用户指定的地方）。

## 第 1 步：收东西，看清楚

让业务同学把资料都给你：文件（xlsx / csv / md / txt / json）、文件夹、飞书或网页链接，加上一段话讲流程。pdf、图片、Word 先请他们导出成 xlsx / csv 或直接贴文字（截图你可以直接看，但每天要用的资料要是能读的文件或链接）。

```bash
python3 -I scripts/inspect_sources.py <文件或文件夹> [...]
```

它列出每个文件里有几张表、表头在第几行、每列会被当成什么（日期 / 产品 / 方向 / 卖点 / 人群 / 数量 / 其它）、日期范围、前几行内容，没有表格的列出前几行文字。读完给每份资料归类：

| 类别 | 认法 | 去哪 |
|---|---|---|
| **任务**（排期、投放计划、需求表） | 有日期 / 数量 / 产品这几列，一行是一批视频 | `sources.schedule` |
| **产品事实**（卖点表、产品手册、机制、价格） | 产品名 + 卖点 / 成分 / 价格 | 每个产品的 config |
| **规则**（QC、审核标准、禁用词、客户反馈） | 「不能」「禁止」「卡审」 | `banned_words`、产品 `rules`；原文放 `sources.qc` |
| **范本**（以前交付过的脚本、爆款稿） | 一段一段的口播文案 | `gold/<key>.json`；整份放 `sources.recent_scripts` |
| **交付要求**（命名规则、交付清单样例） | 文件夹名、链接名的例子 | `delivery_naming` 等 |
| 看不出来的 | | 问用户 |

## 第 2 步：问清流程（一次问完）

把读到的东西和缺的东西放在一起，**一次**问用户。只问资料里看不出来、又会改变做法的事，每个问题给出你猜的答案让他确认。常见要问的：

- 每天谁给任务：是这张表（第几个 sheet、哪几列），还是每天固定做几条，还是每次在对话里说
- 一个 brief 几条视频；一天大概多少条；有没有大促节点
- 脚本谁审、在哪审（对话里说通过 / 飞书文档 / 别的）
- 交付什么：分享链接、命名规则（要一个真实的例子）、要不要 AI 水印
- 写法：开头要落到什么问题（皮肤、头发、厨房油污……），团队最认可哪几条稿
- 平台上每个产品叫什么（Clipo 产品 id），提示词谁来写

[intake.md](intake.md) 是完整清单，拿来对照有没有漏，不用逐条念给用户。

## 第 3 步：建出来

```bash
python3 -I scripts/new_business.py --key <英文key> --brand <品牌名> --out <目录> \
    --products <key>=<产品全名> ... --sources <他们给的文件或文件夹> ...
```

得到一个完整的 skill：脚本、参考文档、空的 config 和 gold，资料拷进 `sources/`。然后**在新目录里**填：

1. **`config/<key>.json`**：只写和默认不一样的（默认值见 `scripts/common.py` 的 `BRAND_DEFAULTS`，字段说明见 [adapt.md](adapt.md)）。`sources` 每个 key 指向归好类的文件（skill 里的文件写 `sources/<文件名>`；每天会更新的用飞书或网页链接）
2. **`config/<key>/<产品>.json`**：从产品资料抄事实，每条写出处（`_note`、`mechanism.source`、`verified_on`）。资料里没有的不编，写进 `open_questions`
3. **`gold/<key>.json`**：从他们的旧稿里每个产品挑 3~5 条，拆成 `beats`（`role` + `text`），标 `product` 和 `direction`
4. **`references/writing.md`**：按他们的写法改骨架和开头（他们的稿是剧情、测评、多人对话的话，照稿子总结一套）
5. **`SKILL.md`**：改 `description`（写清用户说什么话时用它）；按第 2 步的回答改「每日流程」：不需要的步骤删掉，多出来的步骤写进去

**排期表一般不用配**：表头含「日期 / 时间」「产品 / SKU / 店铺」「方向 / 类型」「卖点」「人群」「数量 / 条数」的列自动认，日期 `11.20`、`11月20日`、`2026/11/20`、Excel 日期都认，标题行、合并单元格、多个 sheet 都行；其它列（达人、参考视频、备注）原样带进写稿任务卡。认不出的列才在 `schedule.columns` 写「表头: 字段」。没有排期表的：固定条数写 `daily_quota`，或每次在对话里说，Agent 写一个任务清单交给 `parse_schedule.py --tasks`。

**流程差得多，改脚本**（新 skill 里的 `scripts/` 就是他们自己的，随便改）：

| 他们的流程 | 改法 |
|---|---|
| 资料在别的系统 | `common.fetch_doc` 加一种来源 |
| 不按「每 N 条一个 brief」拆 | `parse_schedule.py` 的 `main`；或每天由 Agent 写 `--tasks` 清单 |
| 只要脚本、不要成片 | `SKILL.md` 流程停在 ⑦（或 `submit --scripts-only`），删掉 ⑧ ⑨ |
| 审核在别处 | 只用 `review_doc.py approve` 记录对话里的审核，或改 `review_doc.py sync` |
| 多一道检查 | `lint_copy.py` 加一条（单句 `lint_text`、整条 `lint_script`） |
| 多一个步骤（比如交付后回填表格） | 在 `scripts/` 加一个脚本，写进 `SKILL.md` 的流程 |

## 第 4 步：用真实的一天跑一遍

在新 skill 目录里跑，用他们表里有任务的某一天：

```bash
python3 -I scripts/fetch_sources.py  --config <key> --run $R
python3 -I scripts/parse_schedule.py --config <key> --run $R --date <那天>     # 产品都对上了
python3 -I scripts/brief_card.py     --config <key> --run $R --brief <一个>   # 照卡写一条
python3 -I scripts/lint_copy.py      --config <key> --run $R
python3 -I scripts/review_doc.py render --config <key> --run $R
python3 -I scripts/clipo_batch.py preflight --config <key> --run $R          # 有平台产品 id 时
```

把写出来的那条脚本和待审文档给用户看。**用户说这条对了**，skill 才算建好；不对就按意见改 config、gold、writing.md，再写一条。不要替用户提交生成（铁律 1、2 在新 skill 里照样有效）。

## 第 5 步：交出去

- 告诉用户新 skill 在哪、怎么装（Claude Code 放 `~/.claude/skills/<name>/`，Codex 放 `~/.codex/skills/<name>/`），以后对 agent 说什么话就会用它
- 列出 `open_questions`：还缺的资料、你猜了没确认的
- 要放 GitHub 先问用户：仓库名、公开还是私有（资料里常有客户文件，默认私有）
