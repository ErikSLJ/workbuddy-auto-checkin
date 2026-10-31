#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WorkBuddy 自动签到 . 云函数入口（腾讯云 SCF / 任意兼容 Python 运行时）

适用场景：用户没有常开电脑 / 软路由，只有手机。把签到逻辑部署到云平台，
由云平台的定时器每天触发，实现"无设备也能自动签到"。

部署包应包含：本文件 main.py + rt_auth.py + workbuddy_checkin.py + push_message.py
（即把本技能的 scripts/ 下这四个文件与 main.py 一起打包成 zip 上传）。

环境变量：
  WB_RT            必需。你的长效刷新令牌（refresh token）。
                   获取方式：在任意装有 WorkBuddy 并登录的电脑上运行
                   `python rt_auth.py --export-rt`，把打印出的一整段令牌粘贴进来。
  WB_LOCALE_TZ     可选。时区，默认 Asia/Shanghai（定时触发器请直接用北京时间 cron）。

令牌自续：每次运行 refresh 后令牌会轮换（旧令牌作废），本函数会把新令牌
回写到函数环境变量 WB_RT（跨冷启动保持）。这需要函数绑定的 CAM 角色具备
scf:UpdateFunctionConfiguration 权限；若未配置，则仅本地持久化（实例冷启动后
可能需重新设置 WB_RT，已在日志中提示）。
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import rt_auth  # noqa: E402

ENV_RT = "WB_RT"


def _persist_rotated(new_rt):
    """把轮换后的新令牌写回，保证云上长期自续。"""
    # 1) 本地落盘（同一实例内热，最先兜底）
    try:
        rt_auth.save_rt(new_rt, source="cloud")
    except Exception:
        pass
    # 2) 回写 SCF 环境变量，跨冷启动保持
    try:
        from tencentcloud.common import credential
        from tencentcloud.common.profile.client_profile import ClientProfile
        from tencentcloud.common.profile.http_profile import HttpProfile
        from tencentcloud.scf.v20180416 import scf_client, models
    except ImportError:
        print("[persist] 未找到 tencentcloud-sdk-python，跳过环境变量回写；"
              "仅本地持久化（实例冷启动后可能需重新设置 WB_RT）")
        return
    secret_id = (os.environ.get("TENCENTCLOUD_SECRET_ID")
                 or os.environ.get("TENCENT_SECRET_ID"))
    secret_key = (os.environ.get("TENCENTCLOUD_SECRET_KEY")
                  or os.environ.get("TENCENT_SECRET_KEY"))
    func_name = (os.environ.get("SCF_FUNCTION_NAME")
                 or os.environ.get("FUNCTION_NAME"))
    ns = os.environ.get("SCF_NAMESPACE") or "default"
    if not (secret_id and secret_key and func_name):
        print("[persist] 缺少腾讯云密钥/函数名，跳过环境变量回写；"
              "仅本地持久化（实例冷启动后可能需重新设置 WB_RT）")
        return
    try:
        cred = credential.Credential(secret_id, secret_key)
        hp = HttpProfile()
        hp.reqTimeout = 10
        cp = ClientProfile()
        cp.httpProfile = hp
        client = scf_client.ScfClient(cred, "ap-guangzhou", cp)
        req = models.UpdateFunctionConfigurationRequest()
        req.FunctionName = func_name
        req.Namespace = ns
        req.Environment = {"Variables": [{"Key": ENV_RT, "Value": new_rt}]}
        client.UpdateFunctionConfiguration(req)
        print("[persist] WB_RT 已回写 SCF 环境变量（跨冷启动保持）")
    except Exception as e:
        print("[persist] 环境变量回写失败: %s（本地仍已保存，下次冷启动可能需重设）" % e)


def main_handler(event, context):
    """SCF 入口。定时器触发时由平台调用，event/context 无需关心。"""
    rt = os.environ.get(ENV_RT)
    if not rt:
        msg = ("[错误] 未设置环境变量 WB_RT。请先在函数配置里填入你的长效令牌"
               "（获取方式见 README：在本机运行 python rt_auth.py --export-rt）。")
        print(msg)
        return {"status": "need_setup", "msg": msg}
    rt_auth.save_rt(rt.strip(), source="env")
    try:
        res = rt_auth.run_rt(do_checkin=True, travel_mode="auto")
    except Exception as e:
        print("[错误] 运行异常: %s" % e)
        return {"status": "error", "msg": str(e)}
    # 取出轮换后的新令牌并持久化
    try:
        cur = rt_auth.read_rt()
        if cur:
            _persist_rotated(cur)
    except Exception:
        pass
    status = res.get("status")
    print("[结果] status=%s msg=%s" % (status, res.get("msg")))
    return {"status": status, "msg": res.get("msg")}


# 本地调试用：直接运行本文件也会执行一次签到
if __name__ == "__main__":
    main_handler(None, None)
