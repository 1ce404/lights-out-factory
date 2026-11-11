# lights-out-factory 黑灯工厂

短视频混剪每日批量生产的 Agent skill 模板。人只做两件事：给资料、审脚本；剩下的 Agent 和平台跑完。

```
排期 / 每日固定条数 → 每 N 条一个 brief → Agent 照团队写法写底稿 → 机器 QC → 人审
→ 审过的文案交给 Clipo Remix 建脚本 → 一次多生成、渲染、平台 AI 审核 → 补够可交付条数 → 每个 brief 一个分享链接
```

从联合利华（清扬、力士）千川混剪的日常生产里抽出来，去掉了品牌数据，规则都放进 config。

## 怎么用：把资料交给 agent，它给你建一个自己业务的 skill

**业务同学看 [SOP.md](SOP.md)**：从装上到每天出片的完整操作步骤。

1. 把这个 skill 装到你的 agent 上（Claude Code：`~/.claude/skills/lights-out-factory/`；Codex：`~/.codex/skills/lights-out-factory/`）
2. 对 agent 说「帮我们业务建一个 skill」，把手上的表全丢过去（排期、产品卖点、QC 标准、以前的脚本、交付命名样例……xlsx / csv / 飞书链接都行），再讲清你们的流程
3. agent 照 [references/onboarding.md](references/onboarding.md)：看清每份资料 → 一次问清流程里看不出来的事 → 建出一个只属于你们业务的 skill，**直接装进你的 agent** → 用真实的一天写一条脚本给你看 → 你认可了就交给你

之后每天对 agent 说「跑今天的排期」「审完了，开始生产」就用你们自己的 skill。新 skill 里的脚本和文档都是你们自己的，想怎么改就怎么改（[references/adapt.md](references/adapt.md)）。

排期表不用改格式：表头含日期 / 产品 / 方向 / 卖点 / 人群 / 数量这些字的列自动认，`11.20`、`11月20日`、`2026/11/20`、Excel 日期都认，标题行、合并单元格、多个 sheet 都行，其它列（达人、参考视频、备注）原样带给写稿的 agent。没有排期表也行：每天固定条数，或每次在对话里说。

手动建也可以：

```bash
python3 -I scripts/new_business.py --key dove --brand 多芬 --agent claude \
    --products bodywash=多芬沐浴露 --sources <你们的文件>
```

先用自带的示例业务试一遍（离线，不连平台、不扣额度）：

```bash
R=/tmp/lof/runs/20261120
python3 -I scripts/fetch_sources.py  --config example --run $R
python3 -I scripts/parse_schedule.py --config example --run $R --date 2026-11-20
python3 -I scripts/brief_card.py     --config example --run $R --brief 1120-B01
# 照任务卡写好 $R/briefs/1120-B01.json 的 segments，然后：
python3 -I scripts/lint_copy.py      --config example --run $R
python3 -I scripts/review_doc.py render --config example --run $R
python3 -I scripts/clipo_batch.py status --config example --run $R
```

## 依赖

Python 3.9+（只用标准库）；能访问 Clipo Remix（⑧ ⑨）。资料在飞书的要装 [`lark-cli`](https://github.com/larksuite)；测配音（`scripts/voice_check.py`）另需 ffmpeg 和 numpy。

支持 skills 的 agent（Claude Code、Codex、Cursor 等）都能用，入口是 `SKILL.md`。

## 目录

| 路径 | 内容 |
|---|---|
| `SOP.md` | 业务同学的使用 SOP |
| `SKILL.md` | 入口：九步流程、铁律 |
| `config/example.json` | 业务共用配置模板（每个字段带 `_note` 说明） |
| `config/example/degreaser.json` | 产品配置模板 |
| `gold/example.json` | 范本库模板 |
| `examples/sources/` | 示例业务的排期、QC、脚本合集（本地文件） |
| `scripts/` | 看资料（`inspect_sources.py`）、建新业务（`new_business.py`）、拉资料、拆排期、写稿任务卡、lint、待审文档、Clipo 批量生产和分享、配音检测 |
| `references/` | 建业务 skill 的步骤（onboarding）、接入清单、改造指南、写法、QC、平台接口 |

每天的运行数据写在 `runs/YYYYMMDD/`，不进仓库。
