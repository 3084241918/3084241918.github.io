# -*- coding: utf-8 -*-
"""Fetch the CSDN blog RSS feed and regenerate works.json.
Stdlib only. Run by GitHub Actions daily; safe to fail (keeps old file)."""
import json
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import date
from email.utils import parsedate_to_datetime

RSS = "https://blog.csdn.net/2601_96964027/rss/list"
BLOG_URL = "https://blog.csdn.net/2601_96964027?type=blog"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

# 依次尝试多个抓取源：CSDN 会屏蔽部分机房 IP，代理源可绕过
SOURCES = [
    ("xml", RSS),
    ("xml", "https://api.allorigins.win/raw?url=" + urllib.parse.quote(RSS, safe="")),
    ("xml", "https://corsproxy.io/?url=" + urllib.parse.quote(RSS, safe="")),
    ("json", "https://api.rss2json.com/v1/api.json?rss_url=" + urllib.parse.quote(RSS, safe="")),
]


def clean(html):
    txt = re.sub(r"<[^>]+>", "", html or "")
    return re.sub(r"\s+", " ", txt).strip()


def parse_date(pub):
    try:
        return parsedate_to_datetime(pub).strftime("%Y-%m-%d")
    except Exception:
        return (pub or "")[:10]


def parse_xml(raw):
    root = ET.fromstring(raw)
    out = []
    for item in root.iter("item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        if title and link:
            out.append({"title": title, "url": link,
                        "date": parse_date(item.findtext("pubDate")),
                        "excerpt": clean(item.findtext("description"))[:120]})
    return out


def parse_json(raw):
    data = json.loads(raw.decode("utf-8"))
    out = []
    for it in data.get("items") or []:
        title = (it.get("title") or "").strip()
        link = (it.get("link") or "").strip()
        if title and link:
            out.append({"title": title, "url": link,
                        "date": parse_date(it.get("pubDate")),
                        "excerpt": clean(it.get("description"))[:120]})
    return out


def fetch_articles():
    for kind, url in SOURCES:
        try:
            req = urllib.request.Request(url, headers=UA)
            raw = urllib.request.urlopen(req, timeout=40).read()
            arts = parse_json(raw) if kind == "json" else parse_xml(raw)
            if arts:
                print("source ok:", url.split("?")[0])
                return arts
            print("source empty:", url.split("?")[0])
        except Exception as e:
            print("source failed:", url.split("?")[0], type(e).__name__, str(e)[:100])
    return []


def main():
    articles = fetch_articles()
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
