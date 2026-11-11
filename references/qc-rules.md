# QC（⑤ ⑦ ⑧ ⑨）

分四层，越往前越便宜：

| 层 | 什么时候 | 谁做 | 拦什么 |
|---|---|---|---|
| 1 脚本 lint | 写完、审核人改完之后 | `lint_copy.py` | 禁用词、极限词、时间承诺、机制数字（及多久没核对）、串系列、产品名缺失 / 被拆开 / 太早 / 卖点句没带、CTA、字幕放不下的长句、素材接不住的场景词、开头撞车。**不查文风** |
| 2 人审脚本 | 每天每个 brief | 审核人 | 口吻、卖点讲没讲清、相似度偏高的、lint 的提醒项 |
| 3 平台 AI 审核 | 每条成片渲染完 | Clipo `video-cuts/review`，按产品提示词 `video_cut_review` | 画面与口播一致、产品外观、画面质量、字幕、音画同步 |
| 4 成片自查 + 人工抽查 | `poll` 收结果时 / 报告出来后 | 脚本 + 你 | 改写违规、水印、语音指令、不稳音色、禁用画面；人看 AI 驳回的，每个 brief 抽 1 条通过的 |

## 层 1：QC 文档 → config

把你们的 QC 文档逐条对到 config。没法机器查的，文案相关的写进产品 `rules`（任务卡会列），画面相关的写进平台提示词。

| QC 条目 | 配置 |
|---|---|
| 广告法：绝对化用语 | `banned_words.error`（首选、唯一、顶级…）+ `regex_error`（最…、第一…，放过「最近 / 第一次」） |
| 广告法：功效夸大 | `banned_words.error`；产品没有资质的功效进产品 `banned_words` |
| 广告法：时间承诺 | `regex_error` 数字 + 小时 / 天 / 周；`regex_warn` 中文数字；`warn`「长效」「持久」 |
| 广告法：权威背书 | `warn`「临床」「专家」「医生」：资料里有出处才能写 |
| 广告法：竞品、价格 | `error` 全网、领先、最低价、原价、性价比 |
| 产品信息与机制准确 | `full_name` 必须完整出现；机制数字只能是 `mechanism.allowed_numbers` |
| 系列不可混淆 | 产品 `foreign_claims` |
| 字幕规范 | `copy_limits.clause_hard_max` / `clause_warn_max`；不带 emoji、`[#…]` |
| 客户近期卡审词 | `banned_words` / 产品 `warn_words` |

QC 文档或客户反馈新增了条目，**先改 config 再写脚本**。

## 层 3：平台 AI 审核

`poll` 在渲染完后自动提交，结论写进 `state.json`：`ai_review` = `pass` / `reject`，`ai_reason` 是原因。审核标准是平台产品提示词 `video_cut_review`，要改告诉用户去平台改（用户明确让你改才改）。平台审核还读产品 `description`，描述里的机制过时会把正确的新机制判错。

平台 AI 审核偶尔误判（把排期指定的卖点判成「无依据」）。看到这类原因告诉用户，由用户决定放行，不自己改结论。改了审核提示词后用 `rereview` 重审被驳回的。

## 层 4：什么算可交付

`clipo_batch.deliverable`：AI 审核通过，并且没有以下任何一项：

| 标记 | 意思 |
|---|---|
| `copy_issues` | 平台改写后的文案 lint 出错误（禁用词、丢产品名、丢卖点、丢 CTA） |
| `watermark_missing` | config 要水印，成片没有 |
| `voice_cmd` | 改写里带了 `[#…]` 语音指令 |
| `bad_voice` | 抽到了 `tts.bad_voices` 里的音色 |
| `voice_drift` | `voice_check.py` 测出段间音高差 ≥ 1.35（听着像两个人） |
| `bad_footage` | 用到了切片描述含 `banned_footage_words` 的画面 |

**不要说「全部通过」**，除非报告里驳回和未完成都是 0、每个 brief 都够数。
