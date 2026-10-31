---
name: workbuddy-auto-checkin-nb
description: "WorkBuddy 自动签到助手 —— 帮用户把 WorkBuddy 自带的「每日签到 + 派猫猫旅行」变成全自动，无需每天手动点。当用户想自动签到、定时签到、挂机签到，或没有软路由/常开电脑、只有手机也想自动签到时使用。触发词：自动签到、定时签到、WorkBuddy 签到、签到脚本、签到机器人、自动领积分、派猫猫旅行自动。适用 Windows / macOS / Linux（本机定时任务）以及云函数（纯手机/无常开设备）。"
display_name: "WorkBuddy签到"
display_name_en: "WorkBuddy Auto Check-in"
description_zh: "把 WorkBuddy 自带的「每日签到 + 派猫猫旅行」变成全自动，无需每天手动点。支持 Windows / macOS / Linux 本机定时任务，也支持腾讯云函数（只有手机、没有常开设备也能用）。一句话触发：帮我自动签到。产出：自动完成每日签到与派猫猫旅行，并返回积分余额与连续签到天数。"
description_en: "Automate WorkBuddy's built-in daily check-in and Buddy cat travel rewards, so you never click manually again. Sets up a native scheduled task on Windows / macOS / Linux, or deploys to a Tencent Cloud serverless function for phone-only users without an always-on device. Just say set up auto check-in: it exports your token, installs the daily schedule, then reports your points balance and streak days."
category: 效率工具
agent_created: true
version: 1.0.0
tags: [自动签到, 定时签到, checkin, workbuddy, 签到脚本, 云函数, 派猫猫旅行, 积分]
---

# WorkBuddy 自动签到助手

> **本质**：本技能帮用户自动完成 WorkBuddy 官方自己的「每日签到」与「派猫猫旅行」
> 领取，把官方接口直签脚本 + 一键定时任务打包好。不是第三方外挂，是对官方功能的自动化。

## 何时使用

- 用户说"帮我自动签到 / 定时签到 / 每天自动领 WorkBuddy 积分"。
- 用户没有软路由、不想折腾路由器，想在**自己的电脑**上挂机签到。
- 用户只有手机、没有常开电脑，想用**云函数**代替设备定时跑。
- 用户想把这套工具**分享给别人**（发技能包 / 部署包）。

## 原理与通道

脚本直接调用 WorkBuddy 官方积分接口，三条通道按需自动择一（由 `scripts/auto_checkin.py` 调度）：

| 通道 | 适用 | 是否需客户端常开 | 定时任务用 |
|------|------|----------------|-----------|
| A 本地登录态 | 本机登录态可直接解密（多数 Windows） | 需要 | 否（用 C 更稳） |
| B 网页会话授权 | macOS 标准安装 / 本地解密失败 | 不需要（一次性授权） | 是 |
| **C 长效令牌** | **一次性导出 refresh token，长期自续** | **不需要** | **✅ 推荐** |

**推荐路径**：一次性 `rt_auth.py --export-rt --save` 把长效令牌存本机 → 定时任务每天跑
`auto_checkin.py --rt`。之后电脑开关机自由，客户端无需常开（令牌 60 天滑动续期，
每日运行即永不过期）。

## 桌面端部署流程（Windows / macOS / Linux）

> 路径约定：`<SKILL_DIR>` 指本 SKILL.md 所在目录；`<PY>` 指 Python 解释器
> （优先用当前运行本技能的 Python：`sys.executable`；找不到时试 `python3` / `python`）。

### Step 0：环境自检（只读，建议先跑）

```bash
<PY> <SKILL_DIR>/scripts/auto_checkin.py --probe
```

报告三条通道的可用性。若本地登录态可读（`channel_local.available=true`）或已有长效令牌，
说明本机取令牌没问题，直接进入 Step 1。

### Step 1：导出长效令牌（只需一次）

**前提**：WorkBuddy 客户端已在本机**登录且处于运行状态**（5.6.2+ 客户端对登录态做了
AtRestEncryption，密钥驻留客户端进程内存，需同用户、同机、客户端运行才能解密）。
若脚本报无法解密，确认客户端已启动登录；仍不行则用通道 B（见下）。

```bash
<PY> <SKILL_DIR>/scripts/rt_auth.py --export-rt --save
```

成功会输出脱敏回执（`rt_saved`），长效令牌已存到 `~/.workbuddy/checkin-rt.json`（权限 600）。
之后客户端是否运行都不再影响签到。

> **通道 B 兜底**（macOS 标准安装或本地解密失败）：按 `scripts/web_auth.py --snippet`
> 取授权码工具，在已登录的 WorkBuddy 网页版 Console 运行，再
> `python web_auth.py --setup-code '<授权码>'` 完成一次性授权。

### Step 2：手动验证一次

```bash
<PY> <SKILL_DIR>/scripts/auto_checkin.py --rt --check-only
```

能正常返回签到状态 / 余额即说明通道打通。再正式跑一次确认领取成功：

```bash
<PY> <SKILL_DIR>/scripts/auto_checkin.py --rt
```

### Step 3：安装系统定时任务

```bash
<PY> <SKILL_DIR>/scripts/setup_scheduler.py            # 每天 09:00
# 可选：
<PY> <SKILL_DIR>/scripts/setup_scheduler.py --time 08:30
<PY> <SKILL_DIR>/scripts/setup_scheduler.py --dry-run  # 只看命令不执行
<PY> <SKILL_DIR>/scripts/setup_scheduler.py --uninstall
```

脚本自动识别系统：
- **Windows** → 任务计划程序 `schtasks`，并写出 `run_checkin.bat` 兜底；
  若 `schtasks` 被策略拦截，会打印一段管理员 PowerShell 命令兜底安装。
- **macOS** → `~/Library/LaunchAgents/com.workbuddy.auto-checkin.plist` + `launchctl load`。
- **Linux** → `crontab` 追加每天 09:00 一行。

### Step 4：核查

看脚本同目录 `checkin.log` 是否每天有记录。或次日手动跑一次确认。
失败推送（可选）：在 `~/.workbuddy/scripts/notify_config.json` 配置渠道（详见
`scripts/push_message.py` 顶部说明），失败时自动提醒。

## 纯手机 / 无常开设备：云函数方案

用户没有常开电脑、只有手机时，把签到部署到云函数，由云平台定时器每天触发。
**完整保姆级步骤见 `references/phone-cloud.md`**，要点：

1. 在任意电脑上 `python rt_auth.py --export-rt` 取令牌（仅需这一次）。
2. 把 `assets/cloud_function/main.py` + `scripts/rt_auth.py` + `workbuddy_checkin.py`
   + `push_message.py` 打包成 zip，上传到腾讯云 SCF（Python 3.10），执行方法 `main.main_handler`。
3. 环境变量 `WB_RT` = 令牌；定时触发器 `0 9 * * *`（北京每天 09:00）。
4. 给函数绑定具备 `scf:UpdateFunctionConfiguration` 的 CAM 角色，令牌轮换后自动回写，长期自续。

## 安全约定（务必遵守）

- 令牌等同账号钥匙，**仅存本机 / 用户自己的云函数环境变量**，绝不进脚本、日志、聊天、仓库。
- 任何输出都不含令牌明文（脚本已做脱敏）；排障时只展示 `xxxx...xxxx` 形态。
- 分享给别人的是**技能包 / 部署包**（不含任何凭据），对方的令牌由各人自己导出。
- 撤销：重新登录 WorkBuddy 客户端即可让旧令牌失效；本机用 `rt_auth.py --forget` 清空。

## 分享与本技能的传播（含返佣，可选）

本技能可打包成 zip 分享给朋友（见 `scripts`/资源，不包含任何私密）。若用户希望分享时
带上自己的返佣入口，可提示用户使用：

- **WorkBuddy 邀请（注册得积分）**：`https://www.workbuddy.cn/events/invite?inviteCode=mw6nom8csl4pfll`
- **方糖 Server 酱（签到失败推送用，注册返佣）**：`https://sct.ftqq.com/r/28382`

> 这两个链接是技能作者的返佣入口，仅在"分享/推荐"场景下向用户说明，不强行塞进脚本逻辑。
> 用户若自己有邀请码，替换即可。

## 排障速查

| 现象 | 原因 | 处理 |
|------|------|------|
| `need_setup`（定时任务跑时） | 没先 `--export-rt --save` | 回到 Step 1 导出令牌 |
| 本地解密失败 `5.6.2+` | 客户端未运行 / 非同用户 | 启动并登录客户端；或改用通道 B |
| Windows `schtasks` 被拦截 | 公司策略 | 用打印出的管理员 PowerShell 命令兜底 |
| 云函数 `need_setup` | `WB_RT` 没填/填错 | 重跑 `rt_auth.py --export-rt` 取令牌填入 |
| 云函数令牌几天后失效 | CAM 角色未授权回写 | 绑定 `scf:UpdateFunctionConfiguration` 权限 |
| 签到 `code=10001` | 今日已签 | 正常幂等，无需处理 |

## 资源清单

- `scripts/auto_checkin.py` —— 统一入口（自动择通道，含 `--probe`）
- `scripts/rt_auth.py` —— 长效令牌通道（导出/刷新/续期）
- `scripts/workbuddy_checkin.py` —— 通道 A 本地登录态 + 签到/旅行核心
- `scripts/web_auth.py` —— 通道 B 网页会话授权
- `scripts/push_message.py` —— 12 类失败推送（可选）
- `scripts/setup_scheduler.py` —— 跨平台定时任务安装器
- `assets/cloud_function/main.py` —— 云函数入口（腾讯云 SCF）
- `references/phone-cloud.md` —— 纯手机/云函数部署保姆级指南
