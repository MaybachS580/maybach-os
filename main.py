"""
Maybach-OS CLI 入口

用法:
    python main.py                 # 交互模式
    python main.py run --task trend_report --keyword AI创业
    python main.py daemon
    python main.py send --message "Hello" --channel wechat
"""

import argparse
import sys
import os

# 添加 src 到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from maybach.core.agent import MaybachAgent
from maybach.notify.notifier import Notifier
from maybach.web_intel.crawler import TrendAnalyzer, WebSearcher
import yaml


def load_config():
    cfg_path = os.path.join(os.path.dirname(__file__), "config.yaml")
    if not os.path.exists(cfg_path):
        cfg_path = os.path.join(os.path.dirname(__file__), "config.example.yaml")
    with open(cfg_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def cmd_run(args):
    """运行指定任务"""
    agent = MaybachAgent()
    agent.boot()

    if args.task == "trend_report":
        keyword = args.keyword or "AI创业 副业"
        days = args.days or 7
        print(f"正在分析: {keyword}（最近{days}天）...")

        analyzer = TrendAnalyzer()
        result = analyzer.analyze(keyword, days=days)
        print("\n" + result["summary"])
        print(f"\n共抓取 {result['total_results']} 条结果")

        # 推送到微信
        config = load_config()
        if config.get("wechat", {}).get("enabled"):
            notifier = Notifier(config)
            report_text = result["summary"] + f"\n\n热词: {', '.join([w for w,_ in result[\"hot_words\"][:5]])}"
            notifier.send_wechat(report_text)
            print("\n✅ 报告已推送到微信")

    elif args.task == "crawl":
        keyword = args.keyword or "创业"
        print(f"正在搜索: {keyword}...")
        searcher = WebSearcher()
        results = searcher.search(keyword, engine=args.engine or "baidu", max_results=args.max_results or 10)
        print(f"\n共 {len(results)} 条结果:")
        for i, r in enumerate(results, 1):
            if "error" not in r:
                print(f"  {i}. {r['title']}")
                print(f"     {r.get('url', '')[:60]}")

    else:
        print(f"未知任务: {args.task}")


def cmd_send(args):
    """发送消息"""
    config = load_config()
    notifier = Notifier(config)
    channel = args.channel or "wechat"
    result = notifier.send(args.message, channels=[channel])
    print(f"发送结果: {result}")


def cmd_daemon(args):
    """后台守护模式"""
    print("迈巴赫 OS 守护模式启动（Ctrl+C 退出）...")
    agent = MaybachAgent()
    agent.boot()
    import time

    while True:
        try:
            if agent.task_queue:
                result = agent.execute_next()
                print(f"[{result.get('task_id','?')}] {result.get('status')} - {result.get('result', result.get('message',''))}")
            time.sleep(60)
        except KeyboardInterrupt:
            print("\n守护进程退出。")
            break


def cmd_shell(args):
    """交互式 Shell"""
    agent = MaybachAgent()
    print(agent.boot())
    print("\n迈巴赫 OS 就绪（输入 q 退出）")
    while True:
        try:
            user_input = input("\n> ").strip()
            if user_input.lower() in ["q", "quit", "exit", "退出"]:
                break
            if not user_input:
                continue
            response = agent.think(user_input)
            print(response)
        except KeyboardInterrupt:
            print("\n再见。")
            break


def main():
    parser = argparse.ArgumentParser(description="Maybach-OS 个人 AI 商业智能体")
    sub = parser.add_subparsers(dest="command")

    # run 命令
    run_parser = sub.add_parser("run", help="运行指定任务")
    run_parser.add_argument("--task", default="trend_report", help="任务类型: trend_report / crawl")
    run_parser.add_argument("--keyword", help="关键词")
    run_parser.add_argument("--days", type=int, help="时间范围（天）")
    run_parser.add_argument("--engine", help="搜索引擎: baidu / bing / duckduckgo")
    run_parser.add_argument("--max-results", type=int, dest="max_results", help="最大结果数")

    # send 命令
    send_parser = sub.add_parser("send", help="发送消息")
    send_parser.add_argument("--message", required=True, help="消息内容")
    send_parser.add_argument("--channel", default="wechat", help="渠道: wechat / feishu / email")

    # daemon 命令
    sub.add_parser("daemon", help="后台守护模式")

    # shell 命令（默认）
    args = parser.parse_args()

    if args.command == "run":
        cmd_run(args)
    elif args.command == "send":
        cmd_send(args)
    elif args.command == "daemon":
        cmd_daemon(args)
    else:
        cmd_shell(args)


if __name__ == "__main__":
    main()
