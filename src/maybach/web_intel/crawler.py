"""
Maybach-OS Web Intelligence 模块
多搜索引擎聚合 + 爬虫框架 + AI 内容分析
"""

import re
import subprocess
import urllib.parse
from datetime import datetime
from typing import Optional


class WebSearcher:
    """
    多搜索引擎聚合搜索

    支持：Baidu / Bing / Google（需代理）/ DuckDuckGo / 微信搜一搜
    """

    def __init__(self):
        self.session_headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        }

    def search(
        self,
        query: str,
        engine: str = "baidu",
        max_results: int = 10,
        days: Optional[int] = None,
    ) -> list[dict]:
        """
        执行搜索

        参数:
            query: 搜索关键词
            engine: baidu / bing / duckduckgo
            max_results: 最大结果数
            days: 限定期数（天）

        返回:
            [{"title", "url", "snippet", "date", "source"}]
        """
        engine = engine.lower()
        if engine == "baidu":
            return self._search_baidu(query, max_results, days)
        elif engine == "bing":
            return self._search_bing(query, max_results, days)
        elif engine == "duckduckgo":
            return self._search_duckduckgo(query, max_results, days)
        else:
            return [{"error": f"不支持的搜索引擎: {engine}"}]

    def _search_baidu(self, query: str, max_results: int, days: Optional[int]) -> list[dict]:
        """百度搜索"""
        url = f"https://www.baidu.com/s?wd={urllib.parse.quote(query)}&rn={max_results}"
        if days:
            url += f"&tn=news&ct=1&lm=-{days * 86400}"

        content = self._fetch(url)
        if not content:
            return [{"error": "百度搜索失败，网络超时"}]

        results = []
        # 简单解析标题和链接（正则方式，生产环境建议用 BeautifulSoup）
        titles = re.findall(r'<h3[^>]*class="[^"]*c-title[^"]*"[^>]*>.*?<a[^>]*>(.*?)</a>', content, re.S)
        links = re.findall(r'<h3[^>]*class="[^"]*c-title[^"]*"[^>]*>.*?<a[^>]*href="([^"]*)"', content, re.S)
        snippets = re.findall(r'<span class="c-span-last">([^<]+)', content)

        for i in range(min(len(titles), max_results)):
            title_clean = re.sub(r'<[^>]+>', '', titles[i] if i < len(titles) else '')
            results.append({
                "title": title_clean.strip(),
                "url": links[i] if i < len(links) else '',
                "snippet": snippets[i].strip() if i < len(snippets) else '',
                "source": "baidu",
                "date": datetime.now().strftime("%Y-%m-%d"),
            })

        return results

    def _search_bing(self, query: str, max_results: int, days: Optional[int]) -> list[dict]:
        """Bing 搜索"""
        encoded_q = urllib.parse.quote(query)
        url = f"https://www.bing.com/search?q={encoded_q}&count={max_results}"
        if days:
            url += f"&qS=1&first=1&setmkt=zh-CN"

        content = self._fetch(url)
        if not content:
            return [{"error": "Bing 搜索失败"}]

        results = []
        titles = re.findall(r'<li[^>]*class="b_algo[^"]*"[^>]*>.*?<h2[^>]*><a[^>]*>(.*?)</a>', content, re.S)
        links = re.findall(r'<li[^>]*class="b_algo[^"]*"[^>]*>.*?<h2[^>]*><a[^>]*href="([^"]*)"', content, re.S)
        snippets = re.findall(r'<p[^>]*>(.*?)</p>', content)

        for i in range(min(len(titles), max_results)):
            title_clean = re.sub(r'<[^>]+>', '', titles[i])
            snippet_clean = re.sub(r'<[^>]+>', '', snippets[i] if i < len(snippets) else '')
            results.append({
                "title": title_clean.strip(),
                "url": links[i] if i < len(links) else '',
                "snippet": snippet_clean.strip(),
                "source": "bing",
                "date": datetime.now().strftime("%Y-%m-%d"),
            })

        return results

    def _search_duckduckgo(self, query: str, max_results: int, days: Optional[int]) -> list[dict]:
        """DuckDuckGo 搜索（无需代理）"""
        encoded_q = urllib.parse.quote(query)
        url = f"https://lite.duckduckgo.com/50x/?q={encoded_q}&ia=web"

        content = self._fetch(url)
        if not content:
            return [{"error": "DuckDuckGo 搜索失败"}]

        results = []
        titles = re.findall(r'<a[^>]*class="result__a[^"]*"[^>]*>(.*?)</a>', content, re.S)
        links = re.findall(r'<a[^>]*class="result__a[^"]*"[^>]*href="([^"]*)"', content, re.S)
        snippets = re.findall(r'<a[^>]*class="result__snippet[^"]*"[^>]*>(.*?)</a>', content, re.S)

        for i in range(min(len(titles), max_results)):
            title_clean = re.sub(r'<[^>]+>', '', titles[i])
            snippet_clean = re.sub(r'<[^>]+>', '', snippets[i] if i < len(snippets) else '')
            results.append({
                "title": title_clean.strip(),
                "url": links[i] if i < len(links) else '',
                "snippet": snippet_clean.strip(),
                "source": "duckduckgo",
                "date": datetime.now().strftime("%Y-%m-%d"),
            })

        return results

    def _fetch(self, url: str) -> Optional[str]:
        """HTTP GET 请求"""
        try:
            result = subprocess.run(
                [
                    "curl", "-s", "-L",
                    "-H", f"User-Agent: {self.session_headers['User-Agent']}",
                    "-H", f"Accept-Language: {self.session_headers['Accept-Language']}",
                    "--max-time", "10",
                    url,
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
            )
            return result.stdout
        except Exception:
            return None


class TrendAnalyzer:
    """
    趋势分析器

    基于关键词聚合多源数据，识别：
    - 高频热词
    - 情感倾向
    - 机会信号
    """

    def __init__(self):
        self.searcher = WebSearcher()

    def analyze(
        self,
        keyword: str,
        engines: Optional[list[str]] = None,
        days: int = 7,
    ) -> dict:
        """
        综合分析一个关键词的趋势

        返回:
            {
                "keyword": str,
                "total_results": int,
                "sources": dict,
                "hot_words": list,
                "opportunity_signals": list,
                "summary": str
            }
        """
        engines = engines or ["baidu", "bing", "duckduckgo"]
        all_results = []

        for engine in engines:
            results = self.searcher.search(keyword, engine=engine, max_results=8, days=days)
            all_results.extend(results)

        # 词频分析（简单实现）
        word_freq = {}
        stop_words = {"的", "了", "是", "在", "和", "与", "为", "对", "有", "等", "或", "而"}

        for r in all_results:
            if "error" in r:
                continue
            words = re.findall(r'[\u4e00-\u9fff]+', r.get("title", "") + r.get("snippet", ""))
            for w in words:
                if len(w) >= 2 and w not in stop_words:
                    word_freq[w] = word_freq.get(w, 0) + 1

        hot_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:10]

        # 机会信号识别
        opportunity_keywords = [
            "红利", "风口", "爆发", "增长", "赚钱", "机遇",
            "补贴", "扶持", "新赛道", "破局", "暴富", "暴增",
            "首次", "限时", "免费", "内测", "招募",
        ]
        signals = []
        for r in all_results:
            if "error" in r:
                continue
            text = r.get("title", "") + r.get("snippet", "")
            for ok in opportunity_keywords:
                if ok in text and r not in signals:
                    signals.append(r)

        return {
            "keyword": keyword,
            "total_results": len([r for r in all_results if "error" not in r]),
            "results_by_source": {e: len([r for r in all_results if r.get("source") == e])
                                  for e in engines},
            "hot_words": [{"word": w, "freq": f} for w, f in hot_words],
            "opportunity_signals": signals[:5],
            "top_results": all_results[:5],
            "summary": self._generate_summary(keyword, hot_words, signals),
        }

    def _generate_summary(
        self,
        keyword: str,
        hot_words: list,
        signals: list,
    ) -> str:
        top_words = ", ".join([w for w, _ in hot_words[:5]])
        signal_count = len(signals)
        opportunity = "高" if signal_count >= 3 else "中" if signal_count >= 1 else "低"

        return (
            f"关键词「{keyword}」综合评估：\n"
            f"  热词: {top_words}\n"
            f"  机会信号数: {signal_count} 条\n"
            f"  机会评级: {opportunity}"
        )


class CrawlerFramework:
    """
    通用爬虫框架

    支持自定义解析规则，可扩展多网站
    """

    def __init__(self):
        self.searcher = WebSearcher()
        self.rules: dict[str, dict] = {}

    def register_rule(self, name: str, rule: dict):
        """注册爬取规则"""
        self.rules[name] = rule

    def crawl(self, url: str, rule_name: Optional[str] = None) -> dict:
        """
        爬取指定 URL

        rule_name: 可选，预注册的规则名称
        """
        content = self._fetch(url)
        if not content:
            return {"status": "error", "message": "请求失败"}

        if rule_name and rule_name in self.rules:
            return self._parse_with_rule(content, self.rules[rule_name])
        else:
            return self._parse_generic(content, url)

    def _fetch(self, url: str) -> Optional[str]:
        return self.searcher._fetch(url)

    def _parse_with_rule(self, content: str, rule: dict) -> dict:
        results = {"status": "success", "url": content[:200]}
        for key, pattern in rule.items():
            matches = re.findall(pattern, content, re.S)
            results[key] = [re.sub(r'<[^>]+>', '', m).strip() for m in matches[:20]]
        return results

    def _parse_generic(self, content: str, url: str) -> dict:
        # 通用解析：提取所有链接和文字段落
        links = re.findall(r'href="(https?://[^"]+)"', content)
        paragraphs = re.findall(r'<p[^>]*>(.*?)</p>', content, re.S)
        clean_paras = [re.sub(r'<[^>]+>', '', p).strip() for p in paragraphs if len(p) > 20]

        return {
            "status": "success",
            "url": url,
            "links": list(set(links))[:20],
            "paragraphs": clean_paras[:10],
        }
