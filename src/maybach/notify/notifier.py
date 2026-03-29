"""
Maybach-OS 推送模块
支持：微信 / 飞书 / Email 多渠道
"""

import json
import os
import subprocess
import sys
from typing import Optional


class Notifier:
    """
    多渠道消息推送中心

    支持：
    - wechat: 通过 pyautogui + 剪贴板模拟微信发送
    - feishu: 飞书开放平台 API
    - email: SMTP 邮件推送
    """

    def __init__(self, config: dict):
        self.config = config
        self.wechat_cfg = config.get("wechat", {})
        self.feishu_cfg = config.get("feishu", {})
        self.email_cfg = config.get("email", {})

    # ──────────────────────────────── 微信 ────────────────────────────────

    def send_wechat(
        self,
        message: str,
        contact: Optional[str] = None,
        use_clipboard: bool = True,
    ) -> dict:
        """
        发送微信消息

        参数:
            message: 要发送的消息内容
            contact: 联系人名称（留空则使用上次联系人）
            use_clipboard: 是否使用剪贴板（推荐 True，避免输入法冲突）
        """
        contact = contact or self.wechat_cfg.get("default_contact", "文件传输助手")

        if not use_clipboard:
            return self._send_wechat_pyautogui(message, contact)

        try:
            return self._send_wechat_clipboard(message, contact)
        except Exception as e:
            return {"status": "error", "channel": "wechat", "message": str(e)}

    def _send_wechat_clipboard(self, message: str, contact: str) -> dict:
        """使用剪贴板 + 坐标点击发送微信消息（Windows）"""

        # 1. 把消息写入剪贴板
        script = f'''
Add-Type -AssemblyName System.Windows.Forms
[System.Windows.Forms.Clipboard]::SetText(@"
{message}
"@)
'''
        subprocess.run(
            ["powershell", "-Command", script],
            capture_output=True,
            text=True,
            encoding="utf-8",
        )

        # 2. 坐标参数
        search_icon_x = self.wechat_cfg.get("search_icon_x", 386)
        search_icon_y = self.wechat_cfg.get("search_icon_y", 462)
        input_x = self.wechat_cfg.get("input_x", 597)
        input_y = self.wechat_cfg.get("input_y", 720)
        send_x = self.wechat_cfg.get("send_x", 1034)
        send_y = self.wechat_cfg.get("send_y", 773)

        # 3. pyautogui 操作序列
        import pyautogui

        pyautogui.PAUSE = 0.3

        # 点击搜索图标
        pyautogui.click(search_icon_x, search_icon_y)
        pyautogui.sleep(0.3)

        # 粘贴联系人名称
        pyautogui.hotkey("ctrl", "a")
        pyautogui.write(contact, interval=0.05)
        pyautogui.sleep(0.5)

        # 回车选择联系人
        pyautogui.press("enter")
        pyautogui.sleep(0.3)

        # 点击输入框
        pyautogui.click(input_x, input_y)
        pyautogui.sleep(0.2)

        # 粘贴消息
        pyautogui.hotkey("ctrl", "v")
        pyautogui.sleep(0.3)

        # 点击发送
        pyautogui.click(send_x, send_y)

        return {
            "status": "success",
            "channel": "wechat",
            "contact": contact,
            "message": message[:50],
        }

    def _send_wechat_pyautogui(self, message: str, contact: str) -> dict:
        """直接 pyautogui.write 发送（不支持中文/emoji）"""
        import pyautogui

        pyautogui.PAUSE = 0.3
        pyautogui.click(386, 462)
        pyautogui.write(contact, interval=0.05)
        pyautogui.press("enter")
        pyautogui.click(597, 720)
        pyautogui.write(message, interval=0.05)
        pyautogui.click(1034, 773)
        return {"status": "success", "channel": "wechat"}

    # ──────────────────────────────── 飞书 ────────────────────────────────

    def send_feishu(
        self,
        message: str,
        receive_id_type: str = "open_id",
        receive_id: Optional[str] = None,
        msg_type: str = "text",
    ) -> dict:
        """
        发送飞书消息

        参数:
            message: 消息内容
            receive_id_type: chat_id / open_id / union_id / email
            receive_id: 接收者 ID
            msg_type: text / post / image / interactive
        """
        app_id = self.feishu_cfg.get("app_id")
        app_secret = self.feishu_cfg.get("app_secret")

        if not app_id or not app_secret:
            return {
                "status": "error",
                "channel": "feishu",
                "message": "飞书配置不完整（app_id/app_secret 未填写）",
            }

        receive_id = receive_id or self.feishu_cfg.get("default_chat_id")

        try:
            # 获取 tenant_access_token
            token_url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
            token_resp = subprocess.run(
                [
                    "curl",
                    "-s",
                    "-X",
                    "POST",
                    token_url,
                    "-H",
                    "Content-Type: application/json",
                    "-d",
                    json.dumps({"app_id": app_id, "app_secret": app_secret}),
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
            )
            token_data = json.loads(token_resp.stdout)
            token = token_data.get("tenant_access_token", "")

            # 发送消息
            msg_url = "https://open.feishu.cn/open-apis/im/v1/messages"
            payload = {
                "receive_id": receive_id,
                "msg_type": msg_type,
                "content": json.dumps({"text": message}),
            }
            msg_resp = subprocess.run(
                [
                    "curl",
                    "-s",
                    "-X",
                    "POST",
                    f"{msg_url}?receive_id_type={receive_id_type}",
                    "-H",
                    f"Authorization: Bearer {token}",
                    "-H",
                    "Content-Type: application/json",
                    "-d",
                    json.dumps(payload),
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
            )
            result = json.loads(msg_resp.stdout)

            if result.get("code") == 0:
                return {
                    "status": "success",
                    "channel": "feishu",
                    "receive_id": receive_id,
                }
            else:
                return {
                    "status": "error",
                    "channel": "feishu",
                    "code": result.get("code"),
                    "message": result.get("msg"),
                }

        except Exception as e:
            return {"status": "error", "channel": "feishu", "message": str(e)}

    # ──────────────────────────────── 邮件 ────────────────────────────────

    def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        smtp_host: Optional[str] = None,
        smtp_port: int = 587,
    ) -> dict:
        """发送邮件"""
        import smtplib
        from email.mime.text import MIMEText

        host = smtp_host or self.email_cfg.get("smtp_host", "smtp.gmail.com")
        username = self.email_cfg.get("smtp_username")
        password = self.email_cfg.get("smtp_password")

        if not username or not password:
            return {
                "status": "error",
                "channel": "email",
                "message": "邮箱配置不完整",
            }

        msg = MIMEText(body, "plain", "utf-8")
        msg["Subject"] = subject
        msg["From"] = username
        msg["To"] = to

        try:
            with smtplib.SMTP(host, smtp_port) as server:
                server.ehlo()
                server.starttls()
                server.login(username, password)
                server.send_message(msg)
            return {"status": "success", "channel": "email", "to": to, "subject": subject}
        except Exception as e:
            return {"status": "error", "channel": "email", "message": str(e)}

    # ──────────────────────────────── 统一发送 ────────────────────────────────

    def send(
        self,
        message: str,
        channels: Optional[list[str]] = None,
        **kwargs,
    ) -> list[dict]:
        """
        统一发送接口

        参数:
            message: 消息内容
            channels: 渠道列表，默认 ["wechat"]
            **kwargs: 透传给各渠道方法
        """
        if channels is None:
            channels = ["wechat"]

        results = []
        for ch in channels:
            if ch == "wechat":
                results.append(self.send_wechat(message, **kwargs))
            elif ch == "feishu":
                results.append(self.send_feishu(message, **kwargs))
            elif ch == "email":
                results.append(self.send_email(message, **kwargs))

        return results
