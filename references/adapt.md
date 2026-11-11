# 改成你自己的业务

这个仓库是一个完整能跑的模板：**整份复制一套，改成你的业务**。最省事的是把资料交给 agent，让它照 [onboarding.md](onboarding.md) 建；这份文档是手动改的说明，也是 agent 填 config 时查字段用的。改的顺序是 config → 范本 → 写法 → 流程；越往后越少需要改。

**config 只写和默认不一样的。** 最小能跑的 config 只有一个品牌名，每个产品只有一个产品名；其它都有默认值（`scripts/common.py` 的 `BRAND_DEFAULTS` / `PRODUCT_DEFAULTS`）。`config/example.json` 是写满的样子，用来查字段。

## 0. 复制

```bash
git clone https://github.com/1ce404/lights-out-factory.git
cd lights-out-factory
python3 -I scripts/new_business.py --key dove --brand 多芬 --out ~/skills/dove-daily-batch \
    --products bodywash=多芬沐浴露 --sources <你们的排期、资料文件>
```

得到一个只属于你们业务的 skill 目录（不带示例数据），下面都在那个目录里改。

然后改 `SKILL.md` 开头的 `name` 和 `description`：`name` 换成你的业务名（如 `dove-daily-batch`），`description` 写清楚**用户说什么话时用它**（「跑今天的排期」「多芬今天的脚本」），agent 靠这一段决定什么时候调用这个 skill。

装到 agent 上：Claude Code 放 `~/.claude/skills/<name>/`，Codex 放 `~/.codex/skills/<name>/`（或在项目里放 `.claude/skills/`）。

## 1. 业务 config：`config/<业务>.json`

复制 `config/example.json`，文件名就是 `--config` 的值。每个字段旁边的 `_note` 写了它是干什么的。最少要改：

| 字段 | 改成 |
|---|---|
| `brand` / `brand_key` / `brand_tag` | 品牌名 / 文件名用的英文 key / 交付命名里的品牌段 |
| `sources` | 你的排期、脚本合集、QC 文档。飞书链接（要装 `lark-cli`）、http 链接、本地文件都行；想多拉一份资料就加一个 key |
| `schedule.columns` | 一般不用写：表头含日期 / 产品 / 方向 / 卖点 / 人群 / 数量这些字的列自动认，各种日期写法都认。认不出的列才写「表头: 字段」。没有排期表就把 `daily_quota` 写成每天固定的产品和条数 |
| `store_to_product` | 排期「产品 / 店铺」列里的字 → 产品 key。不写就按产品名去认 |
| `brief_size` / `generate_factor` | 一个 brief 几条 / 一次多生成几倍 |
| `writing.subject` | 开头要落到的问题，用你们品类的说法（头发状态 / 皮肤状态 / 厨房油污…） |
| `banned_words` | 广告法通用的留着，加上你们 QC 文档、客户卡审的词 |
| `delivery_naming` / `delivery_group_naming` | 客户要的链接、分组命名。可用字段列在 `_naming_note` |
| `campaign` | 大促节点（没有写 `null`） |
| `tts` | 测过稳定的音色；没测过先留空用平台自己的 |

`writing` 里没写的规则用默认值（`scripts/common.py` 的 `WRITING_DEFAULTS`）：开头不报价格机制、产品出现后不写问题又回来、不写时间线、改写不加语音指令。跟你们品类不合适就在 `writing` 里覆盖（都是正则或列表）。

## 2. 每个产品一份：`config/<业务>/<产品key>.json`

复制 `config/example/degreaser.json`。产品 key 就是文件名，要和 `store_to_product` 的值一致。**每条事实都写出处**（`_note`、`mechanism.source`、`verified_on`），lint 会提醒机制多久没核对。

- `full_name` / `name_aliases`：字幕上必须完整出现的产品名
- `clipo_product_id`：平台上的产品 id
- `selling_points`：排期里「测试卖点」那一列的每个值 → 怎么说（`say`）+ 必须出现的词（`must_mention`）
- `mechanism`：机制怎么念、允许出现的数字（别的数字都报错）
- `cta_required`：结尾必须有的词
- `banned_words` / `warn_words` / `foreign_claims`：这个产品不能写的 / 容易卡审的 / 别的产品的卖点
- `footage` / `footage_tags`：平台素材里实际有什么画面（跑 `preflight` 看标签和数量）
- `rules`：其它写法要求，一行一条，任务卡会原样列给写稿的 agent

## 3. 范本：`gold/<业务>.json`

从团队交付过、客户认可的稿里每个产品挑 3~5 条（越多越好，覆盖常用方向），格式照 `gold/example.json`。稿里有违规词的先改干净。agent 写稿学的就是这些；lint 拿它查开头别撞车。用户说好的新稿随时加进来，标 `confirmed`。

## 4. 写法：`references/writing.md`

模板里写的是「5~6 句：开头 → 引产品 → 卖点 → 效果 → 机制 + CTA」这套千川口播带货的写法。你们的写法不一样（剧情、测评、教程、多人对话），就改这份文档和 `scripts/brief_card.py` 里「骨架」那几行，再把对应的范本放进 gold。

## 5. 流程：改脚本

先想清楚是不是真的要改流程，大部分差异 config 就能盖住。真要改：

| 想要 | 改哪里 |
|---|---|
| 资料在 Notion / Google Docs / 内部系统 | `scripts/common.py` 的 `fetch_doc`：加一种来源 |
| brief 不按「每 N 条」拆（一个需求一条、按达人分） | `scripts/parse_schedule.py` 的 `main` |
| 审核不在飞书 | `scripts/review_doc.py`：render 出的 `review.md` 可以贴到任何地方；sync 换成读你的系统；或者只用 `approve` 记录对话里的审核 |
| 加一条 lint 检查 | `scripts/lint_copy.py` 的 `lint_text`（单句）/ `lint_script`（整条）/ `lint_variety`（跨 brief） |
| 只要脚本，不要成片 | 流程停在 ⑦，或跑 `submit --scripts-only` 只建平台脚本 |
| 换生成平台 | `scripts/clipo_batch.py`（`build_script` 建脚本、`gen_body` 生成、`pull_generation` 收结果、`deliverable` 定什么算可交付） |

改了流程，同步改 `SKILL.md` 的「每日流程」：agent 是照它干活的。

## 6. 跑通一遍

```bash
R=runs/$(date +%Y%m%d); C=<你的业务>
python3 -I scripts/fetch_sources.py  --config $C --run $R
python3 -I scripts/parse_schedule.py --config $C --run $R --date $(date +%F)   # 看打印的表，产品都映射上了
python3 -I scripts/clipo_batch.py preflight --config $C --run $R               # 平台产品、素材、提示词都齐
python3 -I scripts/brief_card.py --config $C --run $R --brief <一个>           # agent 照卡写一条
python3 -I scripts/lint_copy.py --config $C --run $R
python3 -I scripts/review_doc.py render --config $C --run $R                   # 给人审
python3 -I scripts/clipo_batch.py submit --config $C --run $R --scripts-only   # 看平台脚本
python3 -I scripts/clipo_batch.py submit --config $C --run $R --dry-run        # 报条数
```

跑之前先拿模板自带的例子试一遍（全离线，不连平台）：`--config example`，`--date 2026-11-20`。

## 7. 一直往回写

跑起来以后，每次被驳回、被客户改、被用户纠正，都写回去：卡审词进 `banned_words`，产品的新要求进 `rules`，好稿进 `gold/`，流程上的坑进 `references/` 对应的文档。**不只留在聊天里**，下次 agent 才会记得。
