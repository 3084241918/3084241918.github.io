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


def clean(html):
    txt = re.sub(r"<[^>]+>", "", html or "")
    return re.sub(r"\s+", " ", txt).strip()


def main():
    req = urllib.request.Request(RSS, headers={"User-Agent": "Mozilla/5.0"})
    xml = urllib.request.urlopen(req, timeout=30).read()
    root = ET.fromstring(xml)
    articles = []
    for item in root.iter("item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        pub = item.findtext("pubDate") or ""
        try:
            d = parsedate_to_datetime(pub).strftime("%Y-%m-%d")
        except Exception:
            d = pub[:10]
        if not title or not link:
            continue
        articles.append({
            "title": title,
            "url": link,
            "date": d,
            "excerpt": clean(item.findtext("description"))[:120],
        })
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
