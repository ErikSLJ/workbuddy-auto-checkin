#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
签到汇总推送（OpenWrt 定时任务用）

读取多个账号的签到报告文件（由 rt_auth.py --report-file 写出），合并成一条消息，
通过 notify_config.json 里配置的 webhook（方糖/微信）统一推送。
在所有账号都跑完后才发一次汇总，避免重复推送。

账号显示名不写死在代码里，而是从同目录可选的私有配置 push_names.json 读取，
例如：{"a1": "自定义名1", "a2": "自定义名2"}
该文件属于使用者本地私有数据，不随分享包/仓库分发；未配置时使用中性的「账号 1 / 账号 2」。

用法（由最后一个账号的 crontab 在签到后调用）：
    python3 push_summary.py
"""
import datetime
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

# (编号, 报告文件路径) —— 与 deploy 脚本里的 --report-file 对应
REPORTS = [
    ("a1", "/root/.workbuddy/checkin_report_a1.json"),
    ("a2", "/root/.workbuddy/checkin_report_a2.json"),
]
CONFIG_PATH = os.path.join(HERE, "notify_config.json")
NAMES_PATH = os.path.join(HERE, "push_names.json")  # 私有，不分发


def load_display_names():
    """读取本地私有显示名配置；任何异常都安全回退到中性名。"""
    names = {}
    try:
        if os.path.isfile(NAMES_PATH):
            with open(NAMES_PATH, "r", encoding="utf-8") as f:
                obj = json.load(f)
            if isinstance(obj, dict):
                for k, v in obj.items():
                    if isinstance(v, str) and v.strip():
                        names[str(k)] = v.strip()
    except Exception:
        pass
    return names


def display_name(key, idx, names):
    return names.get(key) or ("账号 %d" % idx)


def load_report(key, idx, path, names):
    """读取报告；返回 (显示名, data_or_None, err_or_None)。"""
    label = display_name(key, idx, names)
    if not os.path.isfile(path):
        return label, None, "无结果文件（未运行或异常）"
    try:
        with open(path, "r", encoding="utf-8") as f:
            d = json.load(f)
    except Exception as e:
        return label, None, "读取失败：%s" % str(e)[:120]
    today = datetime.date.today().isoformat()
    if d.get("date") != today:
        return label, None, "结果非今日（%s），可能未运行" % d.get("date")
    return label, d, None


def describe(d):
    status = d.get("status")
    action = d.get("action")
    points = d.get("points")
    msg = d.get("msg") or ""
    if status == "ok" and action == "skip_already_signed":
        return "✅ 今日已签（无需重复）"
    if status == "ok" and action == "clicked":
        return "✅ 成功" + ((" +%s" % points) if points else "")
    if status == "ok":
        return "✅ 成功（%s）" % msg
    if status == "need_setup":
        return "⚠️ 未配置令牌（请先 --export-rt --save）"
    return "❌ 失败（%s）" % (msg or "未知原因")


def main():
    today = datetime.date.today().isoformat()
    names = load_display_names()
    acct_lines = []
    any_fail = False
    for idx, (key, path) in enumerate(REPORTS, 1):
        label, d, err = load_report(key, idx, path, names)
        if d is None:
            acct_lines.append("· %s：⚠️ %s" % (label, err))
            any_fail = True
        else:
            acct_lines.append("· %s：%s" % (label, describe(d)))
            if d.get("status") != "ok":
                any_fail = True
    # 方糖 desp 是 Markdown：单个 \n 会被折叠成空格，账号会挤在同一行。
    # 每个账号行尾补两个空格（Markdown 硬换行），标题与正文之间空一行分段，
    # 保证每个账号都独立占一行。
    content = ("【每日签到汇总 %s】\n\n" % today
               + "  \n".join(acct_lines))
    title = "每日签到" + ("：有账号失败，请手动签到" if any_fail else "：全部成功")

    try:
        import push_message
        r = push_message.send_message(title, content, channels=["webhook"],
                                     config_path=CONFIG_PATH)
        print(json.dumps({"status": "pushed", "title": title, "content": content,
                          "result": r}, ensure_ascii=False, indent=2))
    except Exception as e:
        # 推送失败也不影响当天签到；仅记录，便于排查
        print(json.dumps({"status": "push_error", "error": str(e)[:300],
                          "content": content}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
