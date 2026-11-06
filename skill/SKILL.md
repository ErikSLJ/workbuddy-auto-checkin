---
name: workbuddy-auto-checkin-nb
description: "WorkBuddy 自动签到助手（OpenWrt 软路由版）—— 把 WorkBuddy 自带的「每日签到 + 派猫猫旅行」变成全自动，部署到家里的 OpenWrt 软路由，7×24 定时执行，电脑无需常开。当用户想自动签到、定时签到、挂机签到或把签到脚本部署到软路由时使用。触发词：自动签到、定时签到、WorkBuddy 签到、签到脚本、软路由签到、自动领积分、派猫猫旅行自动。"
display_name: "WorkBuddy签到"
display_name_en: "WorkBuddy Auto Check-in"
description_zh: "把 WorkBuddy 自带的「每日签到 + 派猫猫旅行」变成全自动，部署到 OpenWrt 软路由 7×24 定时执行，支持多账号隔离、失败自动重试与合并微信推送。产出：自动完成每日签到与派猫猫旅行，并返回积分余额与连续签到天数。"
description_en: "Automate WorkBuddy's daily check-in and Buddy cat travel rewards on an OpenWrt router, running 24/7 without a computer. Supports isolated multi-account tokens, automatic retries, and one consolidated WeChat push."
category: 效率工具
agent_created: true
version: 1.1.0
tags: [自动签到, 定时签到, checkin, workbuddy, 签到脚本, 软路由, OpenWrt, 派猫猫旅行, 积分]
---

# WorkBuddy 自动签到助手（软路由版）

> **本质**：自动完成 WorkBuddy 官方自己的「每日签到」与「派猫猫旅行」领取，
> 把官方接口直签脚本 + 定时任务打包好部署到 OpenWrt 软路由。不是外挂，是对官方功能的自动化。

## 何时使用

- 用户说「帮我自动签到 / 定时签到 / 每天自动领 WorkBuddy 积分」。
- 用户家里有 **OpenWrt 软路由**，想让签到 7×24 挂在路由器上跑。
- 用户想部署、排查或修改路由器上的自动签到任务。
- 用户想把这套软路由版工具**分享给别人**。

> 本技能**只提供软路由版**，不安装电脑本机定时任务，也不使用云函数。

## 原理与通道

脚本直接调用 WorkBuddy 官方积分接口，`scripts/auto_checkin.py` 自动择一执行：

| 通道 | 适用 | 是否需客户端常开 | 定时任务用 |
|------|------|----------------|-----------|
| A 本地登录态 | 仅用于导出令牌 / 作为公共库 | 需要（仅导出时） | 否 |
| B 网页会话授权 | 本地解密失败时的兜底 | 不需要（一次性授权） | 可用 |
| **C 长效令牌** | **一次性导出 refresh token，长期自续** | **不需要** | **✅ 推荐** |

**推荐路径**：一次性 `rt_auth.py --export-rt --save` 把长效令牌存到路由器 →
crontab 每天跑 `auto_checkin.py --rt`。令牌 60 天滑动续期，每日运行即永不过期。

## 软路由部署流程

> 路径约定：`<SKILL_DIR>` 指本 SKILL.md 所在目录；`<PY>` 指 Python 解释器。

### Step 1：导出长效令牌（只需一次，在已登录的电脑上做）

```bash
<PY> <SKILL_DIR>/scripts/rt_auth.py --export-rt --save
```

成功会输出脱敏回执（`rt_saved`），长效令牌存到 `~/.workbuddy/checkin-rt.json`（权限 600）。
把该文件传到路由器对应的 `HOME/.workbuddy/` 下。之后客户端是否运行都不影响签到。

> 兜底：本地解密失败时可用 `scripts/web_auth.py --snippet` 取授权码工具，
> 在已登录的网页版 Console 运行，再 `--setup-code '<授权码>'` 完成一次性授权。

### Step 2：部署到路由器

把 `scripts/` 下所有脚本 + `notify_config.json` 传至 `/root/.workbuddy/scripts/`，
执行 `deploy_to_openwrt.sh`（或 `setcron.sh` 单独刷新 crontab）。

默认 crontab（两账号隔离，均静默运行、各自写报告文件）：

```cron
30 7 * * * cd /root/.workbuddy/scripts && HOME=/root /usr/bin/python3 auto_checkin.py --rt --no-notify --report-file /root/.workbuddy/checkin_report_a1.json >> checkin.log 2>&1
40 7 * * * cd /root/.workbuddy/scripts && HOME=/root/.workbuddy2 /usr/bin/python3 auto_checkin.py --rt --no-notify --report-file /root/.workbuddy/checkin_report_a2.json >> checkin-acct2.log 2>&1 ; /usr/bin/python3 push_summary.py >> checkin-acct2.log 2>&1
```

- 两个账号靠 **HOME 环境变量**隔离，各读各的 `checkin-rt.json`；
- `--no-notify` 让单次运行不单独推送；
- 最后一个账号跑完后由 `push_summary.py` **合并发一条**微信（方糖）汇总，每个账号独立一行。

### Step 3：只读验证

```bash
<PY> <SKILL_DIR>/scripts/auto_checkin.py --rt --check --no-notify
```

能正常返回签到状态 / 余额即说明通道打通。再看 `checkin.log`、`checkin-acct2.log` 与 `crontab -l`。

## 失败重试与推送规则（务必保留）

- 「已签到」判定必须同时满足：响应确实表示已签（HTTP 2xx 且业务码 10001，
  或消息文案含「已签到 / 今天已签到 / 已领取」）。**绝不能把服务端 5xx 报错误判成已签**。
- 领取接口失败（网络错、HTTP 错、业务码异常）一律进入重试，最多重试 4 次，
  退避间隔递增 **2 / 5 / 10 / 20 秒**。
- 重试期间**不推送**；4 次仍失败才推「签到失败」，提示手动签到。
- 汇总推送内容用 Markdown 硬换行（行尾双空格），保证每个账号独立一行。

## 隐私与脱敏（务必遵守）

- 令牌等同账号钥匙，**仅存路由器本地 / 使用者自己的设备**，绝不进脚本、日志、对话、仓库。
- 任何输出都不含令牌明文（脚本已做脱敏）；排障时只展示 `xxxx...xxxx` 形态。
- **账号显示名不写进任何脚本或分享包**：由路由器本地私有文件 `push_names.json` 提供
  （`{"a1":"自定义名1","a2":"自定义名2"}`），未配置时回退中性的「账号 1 / 账号 2」。
  该文件不随分享包或仓库分发。
- `notify_config.json` 中的方糖 SendKey 只占位，分享包里必须保持占位符。
- 撤销：重新登录 WorkBuddy 客户端即可让旧令牌失效；本地用 `rt_auth.py --forget` 清空。

## 分享与传播（含返佣，可选）

软路由版部署包可分享给朋友（不含任何凭据、不含账号显示名）。若用户希望分享时
带上自己的返佣入口，可提示用户使用：

- **WorkBuddy 邀请（注册得积分）**：`https://www.workbuddy.cn/events/invite?inviteCode=mw6nom8csl4pfll`
- **方糖 Server 酱（签到结果推送用，注册返佣）**：`https://sct.ftqq.com/r/28382`

> 这两个链接是作者的返佣入口，仅在「分享/推荐」场景下向用户说明，不强行塞进脚本逻辑。

## 排障速查

| 现象 | 原因 | 处理 |
|------|------|------|
| `need_setup`（定时任务跑时） | 没先 `--export-rt --save` 或令牌没传到对应 HOME | 重新导出并传到对应目录 |
| 状态查询 `HTTP 500 / code 10001` | 服务端瞬时故障 | 脚本自动重试；不要把 10001 当成已签 |
| 重试 4 次仍失败 | 服务持续不可用 | 会推「签到失败」，手动补签 |
| 汇总推送只有一行 | Markdown 未用硬换行 | 检查 `push_summary.py` 行尾双空格 |
| 方糖推送无结果 | 报告文件不是当天 / 未生成 | 检查 `--report-file` 路径与日期 |

## 资源清单

- `scripts/auto_checkin.py` —— 统一入口（自动择通道）
- `scripts/rt_auth.py` —— 长效令牌通道（导出 / 刷新 / 续期 / 写报告）
- `scripts/workbuddy_checkin.py` —— 签到 / 旅行核心（含重试与已签判定）
- `scripts/web_auth.py` —— 网页会话授权兜底
- `scripts/push_message.py` —— 多渠道推送模块
- `scripts/push_summary.py` —— 多账号结果合并推送
- `deploy_to_openwrt.sh` / `setcron.sh` —— 部署与 crontab 配置
