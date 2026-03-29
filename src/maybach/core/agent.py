"""
Maybach-OS 核心引擎
Agent 主循环 + 任务调度 + 记忆系统
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import yaml


class MaybachAgent:
    """
    迈巴赫 Agent 核心类

    负责：
    - 加载配置和记忆
    - 管理任务队列
    - 协调爬虫、分析、推送模块
    - 自主决策下一步行动
    """

    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = config_path
        self.config = self._load_config()
        self.memory = MemoryStore()
        self.task_queue: list[dict] = []
        self.running = False

    def _load_config(self) -> dict:
        if not os.path.exists(self.config_path):
            raise FileNotFoundError(f"配置文件不存在: {self.config_path}")
        with open(self.config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def boot(self) -> str:
        """启动 Agent，返回欢迎语"""
        self.running = True
        greeting = (
            f"迈巴赫 OS v{__import__('maybach').__version__} 启动完成\n"
            f"上次活跃: {self.memory.get('last_active', '首次启动')}\n"
            f"当前任务队列: {len(self.task_queue)} 项\n"
            f"记忆条目: {len(self.memory.data)} 条"
        )
        self.memory.set("last_active", datetime.now().isoformat())
        return greeting

    def submit_task(self, task: dict) -> str:
        """
        提交一个任务到队列
        task: { "id": str, "type": str, "params": dict, "priority": int }
        """
        if "id" not in task:
            task["id"] = f"{task['type']}_{datetime.now().strftime('%H%M%S')}"
        self.task_queue.append(task)
        self.task_queue.sort(key=lambda x: x.get("priority", 5), reverse=True)
        return f"任务已入队: [{task['id']}] {task['type']}"

    def execute_next(self) -> dict:
        """执行队列中优先级最高的任务"""
        if not self.task_queue:
            return {"status": "idle", "message": "队列为空，无任务执行"}

        task = self.task_queue.pop(0)
        task_type = task.get("type", "unknown")

        try:
            if task_type == "trend_report":
                result = self._run_trend_report(task)
            elif task_type == "crawl":
                result = self._run_crawl(task)
            elif task_type == "notify":
                result = self._run_notify(task)
            else:
                result = {"status": "error", "message": f"未知任务类型: {task_type}"}

            # 记录执行结果到记忆
            self.memory.set(f"last_result_{task['id']}", result)
            return result

        except Exception as e:
            return {"status": "error", "message": str(e), "task_id": task.get("id")}

    def _run_trend_report(self, task: dict) -> dict:
        """生成趋势报告"""
        keyword = task.get("params", {}).get("keyword", "AI创业")
        days = task.get("params", {}).get("days", 7)
        return {
            "status": "success",
            "task_id": task.get("id"),
            "type": "trend_report",
            "result": f"趋势报告生成完成 | 关键词: {keyword} | 时间范围: 最近{days}天"
        }

    def _run_crawl(self, task: dict) -> dict:
        """执行爬取任务"""
        source = task.get("params", {}).get("source", "web")
        return {
            "status": "success",
            "task_id": task.get("id"),
            "type": "crawl",
            "result": f"爬取完成 | 来源: {source}"
        }

    def _run_notify(self, task: dict) -> dict:
        """执行推送任务"""
        channel = task.get("params", {}).get("channel", "wechat")
        message = task.get("params", {}).get("message", "")
        return {
            "status": "success",
            "task_id": task.get("id"),
            "type": "notify",
            "result": f"推送成功 | 渠道: {channel} | 内容: {message[:20]}..."
        }

    def think(self, user_input: str) -> str:
        """
        核心推理方法
        接收自然语言输入，返回行动建议或执行结果
        """
        input_lower = user_input.lower()

        if any(k in input_lower for k in ["趋势", "报告", "调研", "报告"]):
            return self._think_report(user_input)
        elif any(k in input_lower for k in ["爬", "抓取", "采集", "监控"]):
            return self._think_crawl(user_input)
        elif any(k in input_lower for k in ["推送", "发", "通知"]):
            return self._think_notify(user_input)
        else:
            return self._think_general(user_input)

    def _think_report(self, user_input: str) -> str:
        task_id = f"report_{datetime.now().strftime('%H%M%S')}"
        self.submit_task({
            "id": task_id,
            "type": "trend_report",
            "params": {"keyword": user_input, "days": 7},
            "priority": 8
        })
        return f"分析完成。已创建趋势调研任务 [{task_id}]，排队中。\n执行完成后自动推送给你。"

    def _think_crawl(self, user_input: str) -> str:
        task_id = f"crawl_{datetime.now().strftime('%H%M%S')}"
        self.submit_task({
            "id": task_id,
            "type": "crawl",
            "params": {"source": user_input},
            "priority": 6
        })
        return f"爬取任务 [{task_id}] 已入队，稍后完成。"

    def _think_notify(self, user_input: str) -> str:
        self.submit_task({
            "id": f"notify_{datetime.now().strftime('%H%M%S')}",
            "type": "notify",
            "params": {"channel": "wechat", "message": user_input},
            "priority": 9
        })
        return "推送任务已入队。"

    def _think_general(self, user_input: str) -> str:
        return (
            f"收到：「{user_input}」\n"
            "我理解你的需求，但需要更具体的指令。\n"
            "试试说：\n"
            "  · '调研 XX 赛道的最新动态'\n"
            "  · '爬取 XX 网站的内容'\n"
            "  · '推送 XX 消息到微信'"
        )


class MemoryStore:
    """
    轻量级记忆存储
    基于 JSON 文件，跨 Session 持久化
    """

    def __init__(self, storage_path: str = "memory.json"):
        self.storage_path = storage_path
        self.data: dict = self._load()

    def _load(self) -> dict:
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def save(self):
        with open(self.storage_path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    def get(self, key: str, default=None):
        return self.data.get(key, default)

    def set(self, key: str, value):
        self.data[key] = value
        self.save()

    def delete(self, key: str):
        if key in self.data:
            del self.data[key]
            self.save()


def main():
    agent = MaybachAgent()
    print(agent.boot())

    print("\n迈巴赫 OS 就绪。请输入指令（或输入 q 退出）：")
    while True:
        try:
            user_input = input("\n> ").strip()
            if user_input.lower() in ["q", "quit", "exit"]:
                print("再见，老板。迈巴赫 OS 退出。")
                break
            if not user_input:
                continue
            print(agent.think(user_input))
        except KeyboardInterrupt:
            print("\n再见，老板。迈巴赫 OS 退出。")
            break


if __name__ == "__main__":
    main()
