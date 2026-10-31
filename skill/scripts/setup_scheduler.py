#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WorkBuddy 自动签到 . 定时任务安装器（跨平台，纯标准库）

支持：
  Windows  -> 任务计划程序 (schtasks)，并生成 run_checkin.bat 兜底
  macOS    -> launchd (~/Library/LaunchAgents)
  Linux    -> crontab

默认每天 09:00 运行 auto_checkin.py --rt（长效令牌通道，无需 WorkBuddy 客户端常开）。
签到结果写入脚本同目录的 checkin.log，不弹窗、不推送（如需推送请用 notify_config.json）。

用法：
  python setup_scheduler.py               安装每天 09:00 的签到定时任务
  python setup_scheduler.py --time 08:30  自定义时间（24 小时制 HH:MM）
  python setup_scheduler.py --uninstall   卸载定时任务
  python setup_scheduler.py --dry-run     只打印将要执行的命令，不改动系统
  python setup_scheduler.py --with-notify 定时任务也弹桌面通知（默认关闭，静默运行）

注意：
  - 安装前请先 `python rt_auth.py --export-rt --save` 把长效令牌存到本机，
    否则定时任务运行时会报 need_setup。
  - Windows 上 schtasks 在某些被策略限制的机器会失败，此时会自动写出
    run_checkin.bat 并提示用管理员 PowerShell 兜底安装。
"""

import os
import sys
import shutil
import subprocess

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PYTHON = sys.executable
TASK_NAME = "WorkBuddyAutoCheckin"
LAUNCH_LABEL = "com.workbuddy.auto-checkin"
BAT_NAME = "run_checkin.bat"


def _bat_path():
    return os.path.join(SCRIPT_DIR, BAT_NAME)


def _write_bat():
    """写出一个 ASCII 安全的 run_checkin.bat，避免 cmd 中文乱码与引号问题。"""
    bat = _bat_path()
    log = os.path.join(SCRIPT_DIR, "checkin.log")
    lines = [
        "@echo off",
        "cd /d \"%s\"" % SCRIPT_DIR,
        "\"%s\" \"%s\" --rt --no-notify >> \"%s\" 2>&1" % (
            PYTHON, os.path.join(SCRIPT_DIR, "auto_checkin.py"), log),
    ]
    with open(bat, "w", encoding="utf-8") as f:
        f.write("\r\n".join(lines) + "\r\n")
    try:
        os.chmod(bat, 0o755)
    except Exception:
        pass
    return bat


def _run(cmd, dry_run=False, shell=False):
    print("  $ " + (cmd if isinstance(cmd, str) else " ".join(cmd)))
    if dry_run:
        return 0
    try:
        if shell:
            rc = subprocess.call(cmd, shell=True)
        else:
            rc = subprocess.call(cmd)
        return rc
    except Exception as e:
        print("  [错误] 执行失败: %s" % e)
        return -1


# ---------------------------------------------------------------------------
# Windows
# ---------------------------------------------------------------------------
def install_windows(hour, minute, dry_run, with_notify):
    print("[Windows] 任务计划程序")
    if dry_run:
        bat = _bat_path()
        print("  将写出辅助脚本: %s（dry-run 不实际写入）" % bat)
    else:
        bat = _write_bat()
        print("  已写出辅助脚本: %s" % bat)
    tr = "\"%s\"" % bat
    cmd = 'schtasks /Create /TN "%s" /TR %s /SC DAILY /ST %02d:%02d /F' % (
        TASK_NAME, tr, hour, minute)
    rc = _run(cmd, dry_run, shell=True)
    if rc == 0:
        print("  [成功] 定时任务已创建：每天 %02d:%02d 运行。" % (hour, minute))
        return True
    print("  [警告] schtasks 创建失败（可能被策略拦截或权限不足）。")
    print("  兜底方案：以管理员身份打开 PowerShell，粘贴执行：")
    ps = ("$action = New-ScheduledTaskAction -Execute '%s';"
          "$trigger = New-ScheduledTaskTrigger -Daily -At %02d:%02d;"
          "$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType S4U;"
          "Register-ScheduledTask -TaskName '%s' -Action $action -Trigger $trigger -Force"
          ) % (bat, hour, minute, TASK_NAME)
    print("    " + ps)
    print("  或：直接双击 run_checkin.bat 手动跑一次，再决定是否常开电脑。")
    return False


def uninstall_windows(dry_run):
    print("[Windows] 卸载任务计划程序")
    cmd = 'schtasks /Delete /TN "%s" /F' % TASK_NAME
    rc = _run(cmd, dry_run, shell=True)
    if rc == 0:
        print("  [成功] 已删除定时任务。")
    else:
        print("  [提示] 任务可能不存在或删除失败（忽略即可）。")
    return True


# ---------------------------------------------------------------------------
# macOS
# ---------------------------------------------------------------------------
def _launch_plist_path():
    return os.path.expanduser("~/Library/LaunchAgents/%s.plist" % LAUNCH_LABEL)


def install_macos(hour, minute, dry_run, with_notify):
    print("[macOS] launchd")
    args = [PYTHON, os.path.join(SCRIPT_DIR, "auto_checkin.py"), "--rt"]
    if not with_notify:
        args.append("--no-notify")
    plist = _launch_plist_path()
    items = []
    items.append('<?xml version="1.0" encoding="UTF-8"?>')
    items.append('<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" '
                 '"http://www.apple.com/DTDs/PropertyList-1.0.dtd">')
    items.append('<plist version="1.0"><dict>')
    items.append('  <key>Label</key><string>%s</string>' % LAUNCH_LABEL)
    items.append('  <key>ProgramArguments</key><array>')
    for a in args:
        items.append('    <string>%s</string>' % a)
    items.append('  </array>')
    items.append('  <key>StartCalendarInterval</key><dict>')
    items.append('    <key>Hour</key><integer>%d</integer>' % hour)
    items.append('    <key>Minute</key><integer>%d</integer>' % minute)
    items.append('  </dict>')
    items.append('  <key>WorkingDirectory</key><string>%s</string>' % SCRIPT_DIR)
    items.append('  <key>StandardOutPath</key><string>%s</string>'
                 % os.path.join(SCRIPT_DIR, "checkin.log"))
    items.append('  <key>StandardErrorPath</key><string>%s</string>'
                 % os.path.join(SCRIPT_DIR, "checkin.err"))
    items.append('</dict></plist>')
    content = "\n".join(items) + "\n"
    if dry_run:
        print("  将写入: %s" % plist)
        print("  " + content.replace("\n", "\n  "))
    else:
        os.makedirs(os.path.dirname(plist), exist_ok=True)
        with open(plist, "w", encoding="utf-8") as f:
            f.write(content)
        print("  已写入: %s" % plist)
        _run("launchctl load \"%s\"" % plist, dry_run, shell=True)
    print("  [成功] launchd 任务已加载：每天 %02d:%02d 运行。" % (hour, minute))
    return True


def uninstall_macos(dry_run):
    print("[macOS] 卸载 launchd")
    plist = _launch_plist_path()
    _run("launchctl unload \"%s\"" % plist, dry_run, shell=True)
    if not dry_run and os.path.isfile(plist):
        os.remove(plist)
        print("  [成功] 已卸载并删除 plist。")
    else:
        print("  [提示] plist 不存在或已删除。")
    return True


# ---------------------------------------------------------------------------
# Linux
# ---------------------------------------------------------------------------
def _cron_line(hour, minute):
    log = os.path.join(SCRIPT_DIR, "checkin.log")
    return "%d %d * * * \"%s\" \"%s\" --rt --no-notify >> \"%s\" 2>&1" % (
        minute, hour, PYTHON, os.path.join(SCRIPT_DIR, "auto_checkin.py"), log)


def install_linux(hour, minute, dry_run, with_notify):
    print("[Linux] crontab")
    line = _cron_line(hour, minute)
    if dry_run:
        print("  将追加到 crontab: %s" % line)
        return True
    try:
        old = subprocess.check_output(["crontab", "-l"],
                                      stderr=subprocess.DEVNULL).decode("utf-8", "replace")
    except Exception:
        old = ""
    if "auto_checkin.py" in old:
        print("  [提示] 已存在 auto_checkin.py 的 crontab 记录，跳过重复添加。")
        return True
    new = old.rstrip("\n") + "\n" + line + "\n"
    p = subprocess.Popen(["crontab", "-"], stdin=subprocess.PIPE)
    p.communicate(new.encode("utf-8"))
    print("  [成功] 已写入 crontab：每天 %02d:%02d 运行。" % (hour, minute))
    return True


def uninstall_linux(dry_run):
    print("[Linux] 卸载 crontab")
    if dry_run:
        print("  将删除含 auto_checkin.py 的 crontab 行。")
        return True
    try:
        old = subprocess.check_output(["crontab", "-l"],
                                      stderr=subprocess.DEVNULL).decode("utf-8", "replace")
    except Exception:
        print("  [提示] 无 crontab，忽略。")
        return True
    new = "\n".join(l for l in old.splitlines() if "auto_checkin.py" not in l)
    if new.strip():
        p = subprocess.Popen(["crontab", "-"], stdin=subprocess.PIPE)
        p.communicate((new + "\n").encode("utf-8"))
    else:
        _run("crontab -r", False, shell=False)
    print("  [成功] 已删除定时任务。")
    return True


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------
def main():
    args = sys.argv[1:]
    dry_run = "--dry-run" in args
    uninstall = "--uninstall" in args
    with_notify = "--with-notify" in args
    hour, minute = 9, 0
    if "--time" in args:
        try:
            idx = args.index("--time")
            hh, mm = args[idx + 1].split(":")
            hour, minute = int(hh), int(mm)
        except (IndexError, ValueError):
            print("[错误] --time 需为 HH:MM 格式，如 08:30")
            return 2

    print("平台探测: %s" % sys.platform)
    print("Python: %s" % PYTHON)
    print("脚本目录: %s" % SCRIPT_DIR)

    if sys.platform.startswith("win"):
        if uninstall:
            return 0 if uninstall_windows(dry_run) else 1
        return 0 if install_windows(hour, minute, dry_run, with_notify) else 1
    elif sys.platform == "darwin":
        if uninstall:
            return 0 if uninstall_macos(dry_run) else 1
        return 0 if install_macos(hour, minute, dry_run, with_notify) else 1
    else:
        if uninstall:
            return 0 if uninstall_linux(dry_run) else 1
        return 0 if install_linux(hour, minute, dry_run, with_notify) else 1


if __name__ == "__main__":
    sys.exit(main())
