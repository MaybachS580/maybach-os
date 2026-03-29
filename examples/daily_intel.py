"""
迈巴赫情报台 MVP v3
来源：Hacker News + 36kr RSS + 少数派 + TechCrunch + Product Hunt
升级：锁屏检测 + 重试逻辑 + 日志记录
"""

import sys, io, time, re, os, ctypes
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import requests
import pyautogui

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.3

# ── 微信坐标（Rain） ────────────────────────────────
WEIXIN_COORDS = {
    "chat_item":   (512, 319),
    "input_box":   (725, 765),
    "send_button": (1188, 821),
}

# ── 关键词配置（命中 +3分）────────────────────────
KEYWORDS = [
    "AI", "LLM", "大模型", "GPT", "Claude", "Gemini",
    "创业", "融资", "副业", "变现", "独立开发",
    "indie hacker", "saas", "startup", "月收入", "ARR",
    "小红书", "抖音", "私域", "电商", "出海",
    "产品发布", "launch", "工具", "app", "API",
]

# 加权热词（命中 +5分）
HOT_WORDS = [
    "爆火", "暴涨", "突破", "融资", "独角兽", "爆发",
    "viral", "funding", "million", "revenue", "launch",
    "开源", "免费", "薅羊毛", "白嫖",
]

REPORT_DIR = "D:/maybach-mvp/reports"
os.makedirs(REPORT_DIR, exist_ok=True)

# ── 日志 ────────────────────────────────────────
def log(msg):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    log_path = os.path.join(REPORT_DIR, "run.log")
    try:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except:
        pass

# ── 锁屏检测 ────────────────────────────────────
def is_locked():
    """检测 Windows 是否锁屏"""
    try:
        user32 = ctypes.windll.User32
        return user32.GetForegroundWindow() == 0
    except:
        return False

# ── 微信推送（重试3次）───────────────────────────
def _copy(text: str):
    import subprocess
    text = str(text).replace('"', '``"').replace("$", "`$")
    ps = f'Set-Clipboard -Value "{text}"'
    subprocess.run(["powershell", "-Command", ps],
                   capture_output=True, creationflags=0x08000000)

def send_wx(msg: str, retries=3) -> bool:
    for attempt in range(1, retries + 1):
        try:
            log(f"微信推送 第{attempt}次尝试...")
            pyautogui.click(*WEIXIN_COORDS["chat_item"])
            time.sleep(1.2)
            pyautogui.click(*WEIXIN_COORDS["input_box"])
            time.sleep(0.3)
            _copy(msg)
            time.sleep(0.3)
            pyautogui.hotkey("ctrl", "v")
            time.sleep(0.5)
            pyautogui.click(*WEIXIN_COORDS["send_button"])
            time.sleep(0.5)
            log("微信推送成功")
            return True
        except Exception as e:
            log(f"微信推送失败: {e}")
            if attempt < retries:
                time.sleep(3)
    return False

# ── 爬虫：Hacker News ───────────────────────────
def fetch_hn(top_n=20):
    try:
        r = requests.get("https://hacker-news.firebaseio.com/v0/topstories.json", timeout=10)
        ids = r.json()[:top_n]
        stories = []
        for sid in ids:
            try:
                sr = requests.get(f"https://hacker-news.firebaseio.com/v0/item/{sid}.json", timeout=8)
                item = sr.json()
                if item and item.get("title"):
                    stories.append({
                        "title": item["title"],
                        "url": item.get("url", f"https://news.ycombinator.com/item?id={sid}"),
                        "score": item.get("score", 0),
                        "source": "HN",
                    })
            except:
                pass
            time.sleep(0.08)
        return stories
    except Exception as e:
        log(f"HN Error: {e}")
        return []

# ── 爬虫：36kr RSS ──────────────────────────────
def fetch_36kr(top_n=10):
    try:
        r = requests.get("https://36kr.com/feed",
                         headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        text = r.text
        titles = re.findall(r'<title>(.*?)</title>', text)
        links  = re.findall(r'<link><!\[CDATA\[(https://36kr\.com/p/\d+[^]]*)\]\]></link>', text)
        items = []
        for i, (title, link) in enumerate(zip(titles[1:top_n+1], links[:top_n])):
            items.append({
                "title": title.strip(),
                "url": link,
                "score": 50,
                "source": "36kr",
            })
        return items
    except Exception as e:
        log(f"36kr Error: {e}")
        return []

# ── 爬虫：少数派 RSS ────────────────────────────
def fetch_sspai(top_n=10):
    try:
        r = requests.get("https://sspai.com/feed",
                         headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        text = r.text
        titles = re.findall(r'<title>(.*?)</title>', text)
        links  = re.findall(r'<link>(https://[^<\s]+)</link>', text)
        items = []
        for title, link in zip(titles[1:top_n+1], links[:top_n]):
            items.append({
                "title": title.strip(),
                "url": link.strip(),
                "score": 50,
                "source": "少数派",
            })
        return items
    except Exception as e:
        log(f"少数派 Error: {e}")
        return []

# ── 爬虫：TechCrunch RSS ────────────────────────
def fetch_techcrunch(top_n=10):
    try:
        r = requests.get("https://techcrunch.com/feed/",
                         headers={"User-Agent": "Mozilla/5.0"}, timeout=12)
        text = r.text
        titles = re.findall(r'<title>(.*?)</title>', text)
        links  = re.findall(r'<link>(https://techcrunch\.com/[^<\s]+)</link>', text)
        items = []
        for title, link in zip(titles[1:top_n+1], links[:top_n]):
            items.append({
                "title": title.strip(),
                "url": link.strip(),
                "score": 60,  # TechCrunch 有一定专业度
                "source": "TechCrunch",
            })
        log(f"TechCrunch: 获取 {len(items)} 条")
        return items
    except Exception as e:
        log(f"TechCrunch Error: {e}")
        return []

# ── 爬虫：Product Hunt（Atom格式）────────────────
def fetch_producthunt(top_n=10):
    try:
        r = requests.get("https://www.producthunt.com/feed",
                         headers={"User-Agent": "Mozilla/5.0"}, timeout=12)
        text = r.text
        titles = re.findall(r'<title>(.*?)</title>', text)
        # Atom 格式: link alternate href → 只取 /products/ 路径
        links  = re.findall(r'<link[^>]+alternate[^>]+href="([^"]+)"', text)
        links  = [l for l in links if '/products/' in l]
        items = []
        for title, link in zip(titles[1:top_n+1], links[:top_n]):
            items.append({
                "title": title.strip(),
                "url": link.strip(),
                "score": 60,
                "source": "Product Hunt",
            })
        log(f"Product Hunt: 获取 {len(items)} 条")
        return items
    except Exception as e:
        log(f"Product Hunt Error: {e}")
        return []

# ── 过滤 + 评分 ────────────────────────────────
def score_article(article: dict) -> int:
    title = article["title"].lower()
    s = 0
    for kw in KEYWORDS:
        if kw.lower() in title:
            s += 3
    for hw in HOT_WORDS:
        if hw.lower() in title:
            s += 5
    if article.get("score", 0) > 100:
        s += article["score"] // 50
    return s

def filter_and_rank(articles: list, top_n=8) -> list:
    scored = [(score_article(a), a) for a in articles]
    scored.sort(key=lambda x: x[0], reverse=True)
    return [a for _, a in scored if score_article(a) >= 3][:top_n]

# ── 格式化报告 ────────────────────────────────
def build_report(articles: list) -> str:
    now = time.strftime("%m/%d %H:%M", time.localtime())
    header = f"🏎️ 迈巴赫情报台 {now}\n{'='*30}"

    if not articles:
        body = "今日暂无高价值情报，稍后再来看看～"
    else:
        lines = []
        for i, art in enumerate(articles, 1):
            src = art["source"]
            title = art["title"][:55]
            url  = art["url"]
            hot_tag = "🔥" if art.get("score", 0) > 200 else "  "
            lines.append(f"{i}. {hot_tag}{title}")
            lines.append(f"   [{src}] {url}")
        body = "\n".join(lines)

    footer = "="*30 + "\n来源: HN / 36kr / 少数派 / TC / PH"
    return f"{header}\n{body}\n{footer}"

# ── 主流程 ─────────────────────────────────────
def run():
    log("===== 迈巴赫情报台 v3 启动 =====")

    if is_locked():
        log("⚠️ 检测到系统锁屏，跳过本次推送")
        return False

    log("🔍 正在抓取情报...")
    sources = {
        "HN":           fetch_hn(20),
        "36kr":         fetch_36kr(15),
        "少数派":       fetch_sspai(10),
        "TechCrunch":   fetch_techcrunch(10),
        "Product Hunt": fetch_producthunt(10),
    }
    for name, arts in sources.items():
        log(f"   {name}: {len(arts)} 条")

    all_arts = []
    for arts in sources.values():
        all_arts.extend(arts)

    top = filter_and_rank(all_arts)
    log(f"🎯 命中 {len(top)} 条高价值情报")

    report = build_report(top)
    print(report)

    ok = send_wx(report)
    log("✅ 发送成功！" if ok else "❌ 发送失败")

    # 保存报告
    try:
        fname = os.path.join(REPORT_DIR, f"{time.strftime('%Y-%m-%d')}.txt")
        with open(fname, "w", encoding="utf-8") as f:
            f.write(report)
        log(f"报告已保存: {fname}")
    except Exception as e:
        log(f"保存报告失败: {e}")

    return ok

if __name__ == "__main__":
    run()
