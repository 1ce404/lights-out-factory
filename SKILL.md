---
name: lights-out-factory
description: 黑灯工厂：短视频混剪每日批量生产的标准流程模板（排期 → brief → Agent 写底稿 → 机器 QC → 人审 → Clipo Remix 批量生成、渲染、AI 审核 → 补够数 → 分享链接交付）。这是给各业务复制改造的模板，自带一个离线示例业务 `example`。用户说「跑今天的排期」「今天的脚本」「审完了，开始生产」「看下今天生产结果」「今天到哪了」「黑灯工厂」时使用；复制成自己业务的 skill 后，把这段描述改成你们业务的说法。
---

# 黑灯工厂：每日批量混剪

**这是模板。** 每个业务整份复制一套，改成自己的（[references/adapt.md](references/adapt.md)）；开工前要拿到哪些资料见 [references/intake.md](references/intake.md)。仓库自带一个虚构的示例业务 `example`（去油喷雾），资料是本地文件，①~⑦ 全程离线能跑。

排期上每一行 = 店铺 / 产品 × 内容方向 × 测试卖点 × 测试人群 × 数量。**每 `brief_size` 条一个 brief，一个 brief = 一条底稿**。平台按底稿每段都改写出多种说法；平台 AI 审核通过、成片自查也没问题的才算可交付。

**文案 Agent 自己写，片子平台剪。** 平台上只走一条路：**AI 建脚本 → 脚本批量生成混剪 → 批量渲染 → 批量 AI 审核**。画面、配音、BGM、字幕、贴图、音效、改写和审核标准由平台产品提示词决定（`video_script_create` / `video_script_rewrite` / `video_cut_review`），要改去平台改；写文案时也要守平台提示词里的文案规则，`brief_card.py` 会列出来。接口见 [references/clipo-api.md](references/clipo-api.md)。

四条设计：

- **照团队的写法写。** 开头 → 引产品 → 卖点 → 效果 → 机制 + CTA。方向和人群决定开头，开头每条新写；卖点句、机制句用 config 里的固定说法，可以复用；每句写 2~3 个说法给审核人挑、给平台改写当范围。详见 [writing.md](references/writing.md)
- **人只审底稿，必须人审。** lint 查底稿，`poll` 查每条改写和成片，平台 AI 审核查成片
- **文案的事实只有一个来源**：`config/<业务>.json`（共用）+ `config/<业务>/<产品>.json`（每个产品）。规则变了只改那个文件
- **按可交付数交付。** 一次生成排期的 `generate_factor` 倍，不够再补，直到每个 brief 够数；每个 brief 一个分享链接，每天一个业务一个分组

不知道做到哪了，先跑 `status`，它会给出下一步（离线）。

```
① 拉资料 → ② 拆 brief → ③ 平台体检 → ④ 写底稿 → ⑤ lint
   → ⑥ 待审 ⏸ → ⑦ 记录审核 → ⑧ 生成 + 渲染 + AI 审核（不够就补） → ⑨ 交付清单 + 分享链接
```

在技能目录下跑 `python3 -I scripts/<x>.py`。`$R` = 当前项目目录下的 `runs/YYYYMMDD`（运行数据放在 skill 安装目录外），`$C` = 业务 config 名（`config/<C>.json`，示例是 `example`）。一天有几个业务（品牌）时各跑一遍，共用同一个 `$R`：各自用不同的 `brief_prefix`，脚本按 `brand_key` 只读自己的 brief，产出的文件名带 `-<brand_key>`。

| 文件 | 用途 |
|---|---|
| [references/intake.md](references/intake.md) | 接入清单：排期、客户 brief、产品资料、QC、范本、平台准备、交付规格，各写进哪里 |
| [references/adapt.md](references/adapt.md) | 复制模板改成自己的业务：config、范本、写法、流程怎么改 |
| [references/writing.md](references/writing.md) | ④ 写法：骨架、开头、固定说法、每句几个说法、硬性要求、热梗 |
| [references/qc-rules.md](references/qc-rules.md) | 四层 QC；QC 文档 → config 的对应；什么算可交付 |
| [references/clipo-api.md](references/clipo-api.md) | 平台接口和踩过的坑 |
| `config/<业务>.json` | 业务共用：资料来源、排期表头、店铺→产品（或 `daily_quota`）、写法规则、禁用词、文案长度、生成数量、水印、音色、命名 |
| `config/<业务>/<产品>.json` | 每个产品：产品名、平台 id、卖点说法、机制、CTA、卡审词、串系列词、受众、素材画面、固定要求 `rules` |
| `gold/<业务>.json` | 范本库：团队交付过、客户认可的稿，每条标 `product` 和 `direction` |

## 每日流程

**① 拉资料** `fetch_sources.py --config $C --run $R`
把 config `sources` 里的每份资料拉到 `$R/sources/`（飞书链接、网页、本地文件都行）。QC 文档和上次比有变化，新卡审词、新机制先改 config（改机制更新 `verified_on`）。

**② 拆 brief** `parse_schedule.py --config $C --run $R --date 2026-11-20`
核对打印的表，店铺都映射到产品；找不到当天的行就停，告诉用户排期没更新。没有排期表的业务按 `daily_quota` 直接拆。用户只要某个产品时加 `--product`。

**③ 平台体检** `clipo_batch.py preflight --config $C --run $R`
查平台上每个产品：能不能打开、有没有可用素材、风险切片、产品描述里机制对不对、有没有自己的建脚本提示词、提示词里写的音效贴图分类平台上有没有、审核提示词的产品名对不对。有问题告诉用户去平台改，不自己改平台。

**④ 写底稿** `brief_card.py --config $C --run $R [--brief <id>]`
每个 brief 打一张任务卡，Agent 照卡写，填进 brief 的 `segments`（每段 `role` / `title` / `text`，`alt` 写另外 1~2 个说法，画面对不上的写 `visual_tags`）。用户要结合热点时按 [writing.md](references/writing.md) 第 8 节查热梗写进 `$R/hotspots.json`。用户给了结构就照结构写，填 `template`。

**⑤ lint** `lint_copy.py --config $C --run $R`
错误清零才能给人审。查事实、合规、产品名位置、卖点、机制、CTA、短句长度（每句和每个备选说法都查），以及开头撞车。不查文风。

**⑥ 待审 ⏸** `review_doc.py render --config $C --run $R` → `review-<C>.md` / `review-<C>.xml`
把每条脚本完整发给用户看（完整口播、分段、备选说法、开头最像的旧稿）。要发飞书：`lark-cli docs +create --content @$R/review-<C>.xml`，**第一次往外部文档写、往群里发之前先问用户**放哪。**然后停下等审核**。

**⑦ 记录审核**
- 用户在对话里说通过：`review_doc.py approve --brief <id> --by 用户 --note "<原话>"`
- 在文档里审完：`review_doc.py sync --doc <链接>`，审核人改过的句子记进 `learned/`

**只有这两条路能标通过**，都会记下当时的文案。手改 `status`、审过后又改文案，`submit` 都会拦下，要重新给人看。

**⑧ 生产**
```bash
python3 -I scripts/clipo_batch.py submit --config $C --run $R --scripts-only   # 只建平台脚本并核对，不生成、不扣额度
python3 -I scripts/clipo_batch.py submit --config $C --run $R --dry-run        # 报总条数给用户确认（消耗额度）
python3 -I scripts/clipo_batch.py submit --config $C --run $R
python3 -I scripts/clipo_batch.py poll   --config $C --run $R --wait 3600      # 后台跑
```
- **AI 建脚本**：把审过的文案逐字交给平台，平台按产品提示词配其余的；建完按 `naming` 命名、每段开 AI 改写、把审过的备选说法和 `writing.rewrite_rules` 写进这条脚本的改写要求、换成 `tts` 里的稳定音色、按 `visual_tags` 改画面标签，再读回核对，对不上就删掉不生成
- **生成**：每个 brief 生成 排期 × `generate_factor` 条；平台上一个 brief 一条生成任务，每轮 ≤ `generate_chunk` 条，后面的轮次在同一条任务上 continue。每条都加合规水印（`watermark`）
- **渲染 + 审核**：`poll` 给每条剪辑提交渲染，渲染好的一批提交 AI 审核，并自查改写违规、水印、语音指令、不稳音色、禁用画面（[qc-rules.md](references/qc-rules.md) 层 4）。`voice_check.py`（要 numpy + ffmpeg，不加 -I 跑）测段间音高差
- 某轮失败：`submit --retry-failed` 在同一条任务上继续
- 改了平台审核提示词或放宽了 config 规则：`rereview` 重审被驳回的。它和后台 `poll` 都写进度，先停 `poll` 再跑
- 有 brief 不够数：`topup --dry-run` 报补多少，用户确认后 `topup`，再 `poll`。同一份审过的脚本，不用重审

**⑨ 交付**
```bash
python3 -I scripts/clipo_batch.py report --config $C --run $R              # report.md（每条结果和驳回原因）+ delivery.md（交付清单）
python3 -I scripts/clipo_batch.py share  --config $C --run $R --dry-run
python3 -I scripts/clipo_batch.py share  --config $C --run $R              # 每个够数的 brief 一个分享链接，当天收进一个分组
```
- 链接名按 `delivery_naming`，分组名按 `delivery_group_naming`。**链接名是客户看的，要准**
- 不够数的 brief 默认不发，要先发加 `--partial`；补生成后挑的视频变了，再跑 `share` 会换成新链接（分组里自动替换，旧链接删除）

回复用户：每个 brief 可交付 / 排期条数、驳回原因分类、没生产的、要人决定的事；最后给一段**能直接复制**的链接清单（代码块，分组链接在前，每行「交付名：链接」）。有 brief 不够数就不说「全部够数」。

## 铁律

1. **脚本必须人审**：「直接生成」不等于审过，先给人看脚本；不替人填审核结论
2. **提交前报条数**：每次 submit / topup 都先 dry-run，告诉用户要生成多少条，确认后再提交
3. **事实只来自 config 和当天资料**；不编亲测或他人背书；每段都开 AI 改写，改写违规一律当驳回
4. **不替人改共享的东西**：不改客户共享文档，不改 / 删平台上的产品、素材、分类和产品提示词。片子的样子要变，告诉用户去平台改
5. **学到的写回去**：卡审词、机制、素材画面、产品的写法要求进 config；用户说好的脚本进 `gold/`；平台那边的问题告诉用户；不只留在聊天里
