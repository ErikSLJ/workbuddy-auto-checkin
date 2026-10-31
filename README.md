# WorkBuddy 自动签到 · 社区分享工具

把 WorkBuddy 的「每日签到 / 派猫猫旅行」变成全自动：装好一次，电脑、云函数或 OpenWrt 软路由每天定时帮你完成，积分稳稳到账。

> ⚠️ **这是社区个人分享，非 WorkBuddy 官方出品。** 自动签到的能力来自 WorkBuddy 自身功能，本工具仅做自动化封装。

---

## 两种版本，按需下载

| 版本 | 适合 | 下载 |
| --- | --- | --- |
| **电脑 / 云函数版** | Windows / macOS / Linux，或纯手机用户（用腾讯云 SCF 托管） | [workbuddy-auto-checkin.zip](https://raw.githubusercontent.com/ErikSLJ/workbuddy-auto-checkin/main/workbuddy-auto-checkin.zip) |
| **OpenWrt 软路由版** | 已有 OpenWrt 软路由，想 7×24 挂机 | [workbuddy-checkin-openwrt.zip](https://raw.githubusercontent.com/ErikSLJ/workbuddy-auto-checkin/main/workbuddy-checkin-openwrt.zip) |

两个压缩包也都在本仓库根目录，可直接 Clone 后使用。

---

## 怎么用

### 电脑 / 云函数版（WorkBuddy 技能）

1. 下载 `workbuddy-auto-checkin.zip` 并解压。
2. 把解压出来的 `skill/` 整个目录，放进 WorkBuddy 的技能目录（或在 WorkBuddy 里加载本地技能）。
3. 在 WorkBuddy 对话里说一句「帮我自动签到」，它会自动导出你的登录态、建立每天 9 点的定时任务。
4. 之后每天自动签到 + 派猫猫旅行，令牌 60 天自动续期，基本不用管。

纯手机用户：技能包内附「云函数」模板，部署到腾讯云 SCF 即可（平台定时器每天触发，手机只管一次部署）。

### OpenWrt 软路由版

1. 下载 `workbuddy-checkin-openwrt.zip` 并解压。
2. 按压缩包内的图文教程，把签到脚本传到软路由并设为开机自启。
3. 教程已适配新 / 老固件，会自动识别该用哪把 SSH 密钥。

---

## 在线文档与留言

- **图文落地页（含使用演示、收益说明、安全说明）：** https://wb-auto-checkin-16525.app.workbuddy.host
- 落地页内置**留言板**：用邮箱验证码注册 / 登录后即可留言提问（当前免费，付费高级功能后续开放）。

---

## 安全说明（透明）

- 工具包里**没有任何作者的私密信息**：不含我的令牌、密钥、路由器 IP。
- 签到用的是**你自己的 WorkBuddy 账号**：工具只在你本机 / 你自己的云函数里导出并保存你的登录态，全程不离开你的设备；朋友各自导出自己的，互不干扰。
- 令牌为离线长效令牌，60 天滑动续期，过期后工具会自动提示重新导出一次。

---

## 收益相关（可选）

- **邀请有奖：** 通过落地页顶部「先注册 WorkBuddy」按钮注册，邀请人可获得官方奖励，你本人也得 2000 积分——双赢。
- **方糖推送（可选）：** 想让签到失败时用微信通知你，可自备 [方糖 Server酱](https://sct.ftqq.com/r/28382) 推送 key（走此返佣链接注册，邀请人也有返佣）。不填也能正常签到，只是没有微信提醒。

---

## 目录结构

```
workbuddy-auto-checkin/
├── README.md                      本文件
├── workbuddy-auto-checkin.zip     电脑 / 云函数版（技能包）
├── workbuddy-checkin-openwrt.zip  OpenWrt 软路由版
└── skill/                        WorkBuddy 技能源码
    ├── SKILL.md
    ├── README.md
    ├── scripts/                   签到 / 认证 / 定时任务等脚本
    ├── assets/cloud_function/     云函数模板
    └── references/                参考资料
```

---

## 免责声明

本仓库仅供学习与交流。使用本工具产生的任何账号风险、收益变化或第三方服务费用，均由使用者自行承担。请遵守 WorkBuddy 及相关平台的使用条款。
