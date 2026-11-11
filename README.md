# lights-out-factory 黑灯工厂

短视频混剪每日批量生产的 Agent skill 模板。人只做两件事：给资料、审脚本；剩下的 Agent 和平台跑完。

```
排期 / 每日固定条数 → 每 N 条一个 brief → Agent 照团队写法写底稿 → 机器 QC → 人审
→ 审过的文案交给 Clipo Remix 建脚本 → 一次多生成、渲染、平台 AI 审核 → 补够可交付条数 → 每个 brief 一个分享链接
```

从联合利华（清扬、力士）千川混剪的日常生产里抽出来，去掉了品牌数据，规则都放进 config。

## 怎么用：每个业务整份复制一套

1. **先问齐资料**：[references/intake.md](references/intake.md) —— 排期、客户 brief、产品资料、QC 标准、团队范本、平台上的产品和提示词、交付命名，各写进哪里
2. **复制改造**：[references/adapt.md](references/adapt.md) —— 改 config、放范本、改写法，必要时改流程
3. **跑起来**：对 agent 说「跑今天的排期」「审完了，开始生产」「今天到哪了」。流程见 [SKILL.md](SKILL.md)

```bash
git clone https://github.com/1ce404/lights-out-factory.git my-business-factory
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
| `SKILL.md` | 入口：九步流程、铁律 |
| `config/example.json` | 业务共用配置模板（每个字段带 `_note` 说明） |
| `config/example/degreaser.json` | 产品配置模板 |
| `gold/example.json` | 范本库模板 |
| `examples/sources/` | 示例业务的排期、QC、脚本合集（本地文件） |
| `scripts/` | 拉资料、拆排期、写稿任务卡、lint、待审文档、Clipo 批量生产和分享、配音检测 |
| `references/` | 接入清单、改造指南、写法、QC、平台接口 |

每天的运行数据写在 `runs/YYYYMMDD/`，不进仓库。
