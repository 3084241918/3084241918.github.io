# -*- coding: utf-8 -*-
"""Fetch CSDN blog articles via the community API and regenerate works.json.

Primary source: CSDN get-business-list API (returns title/url/desc/date + all stats).
Fallback: scrape the blog list page HTML.
Stdlib only. Run by GitHub Actions daily; safe to fail (keeps old file)."""
import json
import re
import sys
import urllib.request
import urllib.parse
from datetime import date

USERNAME = "2601_96964027"
BLOG_URL = f"https://blog.csdn.net/{USERNAME}?type=blog"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

API = (f"https://blog.csdn.net/community/home-api/v1/get-business-list"
       f"?page=1&size=50&businessType=blog&orderby=&noOverSelf=false&username={USERNAME}")

# 代理源（CSDN 会屏蔽部分机房 IP，代理可绕过）
PROXIES = [
    lambda u: u,  # 直连
    lambda u: "https://api.allorigins.win/raw?url=" + urllib.parse.quote(u, safe=""),
    lambda u: "https://corsproxy.io/?url=" + urllib.parse.quote(u, safe=""),
    lambda u: "https://api.codetabs.com/v1/proxy?quest=" + urllib.parse.quote(u, safe=""),
]


def clean(html):
    txt = re.sub(r"<[^>]+>", "", html or "")
    return re.sub(r"\s+", " ", txt).strip()


def parse_date(s):
    return (s or "")[:10]


def fetch_via_api():
    """用 CSDN get-business-list API 抓取文章 + 统计数据。"""
    hdrs = dict(UA)
    hdrs["Referer"] = BLOG_URL
    for proxy in PROXIES:
        url = proxy(API)
        try:
            req = urllib.request.Request(url, headers=hdrs)
            data = json.loads(urllib.request.urlopen(req, timeout=40).read().decode("utf-8"))
            out = []
            for it in ((data.get("data") or {}).get("list")) or []:
                title = (it.get("title") or "").strip()
                link = (it.get("url") or "").strip()
                if not (title and link):
                    continue
                out.append({
                    "title": title,
                    "url": link,
                    "date": parse_date(it.get("postTime")),
                    "excerpt": clean(it.get("description"))[:120],
                    "views": it.get("viewCount") or 0,
                    "diggs": it.get("diggCount") or 0,
                    "collects": it.get("collectCount") or 0,
                    "comments": it.get("commentCount") or 0,
                })
            if out:
                print("api ok:", url.split("?")[0], "articles:", len(out))
                return out
            print("api empty:", url.split("?")[0])
        except Exception as e:
            print("api failed:", url.split("?")[0], type(e).__name__, str(e)[:100])
    return []


def fetch_via_html():
    """备用：直接抓取博客列表页 HTML 解析文章（无统计数据）。"""
    hdrs = dict(UA)
    hdrs["Accept"] = "text/html,application/xhtml+xml"
    for proxy in PROXIES:
        url = proxy(BLOG_URL)
        try:
            req = urllib.request.Request(url, headers=hdrs)
            raw = urllib.request.urlopen(req, timeout=40).read().decode("utf-8", "ignore")
            links = re.findall(rf'https://blog\.csdn\.net/{USERNAME}/article/details/\d+', raw)
            # 去重保持顺序
            seen, out = set(), []
            for l in links:
                if l in seen:
                    continue
                seen.add(l)
                # 尝试从链接附近提取标题
                m = re.search(r'href="' + re.escape(l) + r'"[^>]*>([^<]{2,80})<', raw)
                title = clean(m.group(1)) if m else "未命名文章"
                out.append({"title": title, "url": l, "date": "", "excerpt": "",
                            "views": 0, "diggs": 0, "collects": 0, "comments": 0})
            if out:
                print("html ok:", url.split("?")[0], "articles:", len(out))
                return out
            print("html empty:", url.split("?")[0])
        except Exception as e:
            print("html failed:", url.split("?")[0], type(e).__name__, str(e)[:100])
    return []


def main():
    articles = fetch_via_api()
    if not articles:
        articles = fetch_via_html()
    if not articles:
        sys.exit("no articles parsed; keep existing works.json")
    data = {
        "blog": {"name": "晴天遇见枫", "url": BLOG_URL},
        "updated": date.today().isoformat(),
        "articles": articles,
    }
    with open("works.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print("works.json updated: %d articles" % len(articles))


if __name__ == "__main__":
    main()
