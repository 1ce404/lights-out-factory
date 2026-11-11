# 接入清单：开工前要拿到的东西

新业务接进来之前，照这张表对一遍资料齐不齐（agent 建 skill 时照 [onboarding.md](onboarding.md)，用这张表查漏）。**左边没拿到的，右边那一步就跑不起来**；拿到之后写进哪里也列出来了。「必须」的缺了先别开工，「建议」的缺了能跑，但会更容易被驳回、更容易重复。

## 一、任务从哪来（每天变）

| 资料 | 必须？ | 问谁要 | 写进 | 用在 |
|---|---|---|---|---|
| **排期表**：哪天、哪个产品、什么内容方向、测试卖点、测试人群、几条（xlsx / csv / 飞书表格都行，表头和日期写法自动认，多出来的列带进任务卡） | 必须（三选一） | 投放 / 运营 | `sources.schedule` | ② 拆 brief |
| 或者**每天固定条数**（没有排期表的业务） | 必须（三选一） | 客户 / 项目经理 | `daily_quota` | ② 拆 brief |
| 或者**每次在对话里说**要做什么 | 必须（三选一） | 业务同学 | Agent 写成任务清单，`parse_schedule.py --tasks` | ② 拆 brief |
| **客户 brief / 需求文档**：这次要推什么、主张、禁区、节点（双十一、618） | 建议 | 客户 / AM | 事实进产品 config（卖点、机制、rules）；节点进 `campaign`；原文可加一个 `sources.client_brief` 每天拉下来对照 | ④ 写稿 |
| **直播 / 活动机制**：价格、赠品、拍几发几，什么时候换 | 必须（念机制的业务） | 运营 | 产品 `mechanism.spoken` / `allowed_numbers` / `verified_on` | ④ 写稿、⑤ lint |

## 二、能写什么、不能写什么（偶尔变）

| 资料 | 必须？ | 写进 | 用在 |
|---|---|---|---|
| **产品资料**：全名（字幕上必须一字不差的写法）、卖点、成分 / 技术、用法、规格 | 必须 | `config/<业务>/<产品>.json`：`full_name`、`name_aliases`、`selling_points`、`keep_terms` | ④ ⑤ |
| **QC / 审核标准**：广告法禁用词、品类禁用词、客户近期卡审词、字幕规范 | 必须 | `banned_words`（品牌共用）、产品的 `banned_words` / `warn_words`、`copy_limits`；原文放 `sources.qc` 每天拉下来比对变化 | ⑤ lint |
| **同品牌其它产品的卖点**（防止串系列） | 建议 | 产品的 `foreign_claims` | ⑤ |
| **受众和口吻**：谁在说、对谁说、男声女声 | 必须 | 产品的 `audience_note`、`speaker_warn`、`voice_gender` | ④ 写稿、配音 |
| **团队交付过、客户认可的脚本**（每个产品 3~5 条以上，最好覆盖常用方向） | 必须 | `gold/<业务>.json`（每条写 `product`、`direction`）；更多的整份放 `sources.recent_scripts` | ④ 学写法、⑤ 查开头撞车 |
| **写法**：开头要落到什么问题（头发、皮肤、油污…）、开头的几种类型 | 建议 | `writing.subject`、`writing.opening_types` | ④ |

## 三、平台上要先准备好的（由业务同学在 Clipo 平台做）

| 东西 | 必须？ | 检查 |
|---|---|---|
| **平台产品**，每个产品一个，拿到 id | 必须 | 产品的 `clipo_product_id`；`preflight` 能打开 |
| **素材切片**，打好标签，风险切片清掉 | 必须 | `preflight` 列出可用数、空标签、风险数；把有素材的标签抄进产品的 `footage_tags`，画面写进 `footage` |
| **建脚本提示词** `video_script_create`：配音、BGM、字幕样式、每段画面标签、贴图、音效 | 必须 | `preflight` 拦「没有 / 平台默认 / 允许乱搜音效」 |
| **改写提示词** `video_script_rewrite` | 建议 | 不写用平台默认 |
| **审核提示词** `video_cut_review`：QC 标准 + 这个产品的专属标准 | 必须 | `preflight` 核对里面写的产品名 |
| **产品描述**：当前机制写对（AI 审核会读它） | 建议 | `preflight` 提醒机制不在描述里 |
| **不能用的画面**（比如客户说不要的某类镜头） | 建议 | `banned_footage_words`（按切片描述查） |
| **稳定的音色**（实测段与段之间不变声） | 建议 | `tts.voices` / `voices_by_gender`；新音色先用 `voice_check.py` 测 |

## 四、交付成什么样

| 问题 | 写进 |
|---|---|
| 每天交付什么：分享链接？下载包？每个 brief 几条？ | `brief_size`（一个 brief 几条），`share` 每个 brief 一个链接，当天一个分组 |
| 链接 / 文件夹怎么命名（**客户看的就是它，要准**） | `delivery_naming`、`delivery_group_naming`；用到的字段（产品代号、克数、视频类型）写进产品的 `naming_code` / `naming_grams`、`direction_tags` |
| 要不要 AI 生成水印、放哪 | `watermark` |
| 一次多生成几倍（AI 审核通过率低就多生成） | `generate_factor` |
| 谁审脚本、在哪审（对话里 / 飞书文档 / 别的） | 流程 ⑥ ⑦；飞书的话 `review.doc_parent_token` |

## 五、流程要不要改

默认流程见 [SKILL.md](../SKILL.md)。下面这些情况才要改流程本身（改法见 [adapt.md](adapt.md)）：

- 不是「排期 → 每 N 条一个 brief」，而是「一个需求一条脚本」「按达人分」→ 改 `parse_schedule.py` 生成 brief 的方式
- 不用 Clipo 生成，或者只要脚本不要成片 → ⑧ ⑨ 停在 `submit --scripts-only`，或换掉 `clipo_batch.py`
- 审核在别的系统（Notion、企业微信、表格）→ 改 `review_doc.py` 的 render / sync，或只用 `approve` 记录对话里的审核
- 资料在别的地方（Notion、Google Docs、内部系统）→ 在 `common.fetch_doc` 里加一种来源

**拿齐之后**：照 [adapt.md](adapt.md) 填 config，用一个真实的一天跑一遍：`fetch_sources` → `parse_schedule` → `preflight` → `brief_card` 写一条 → `lint_copy` → 给人审 → `submit --scripts-only` 看平台脚本 → `submit --dry-run`。
