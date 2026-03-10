"""
trend_scanner.py - IMPROVED
────────────────────────────
Removed pytrends (Google keeps breaking it).
Now uses Google Trends RSS feed instead - much more reliable.
Sources: Google Trends RSS, Reddit (14 subreddits), Wikipedia, HackerNews, RSS feeds
"""

import json
import time
import requests
from datetime import datetime
from bs4 import BeautifulSoup
import os
from dotenv import load_dotenv

load_dotenv()

NICHE_KEYWORDS = os.getenv(
    "NICHE_KEYWORDS",
    "engineering,science,history,technology,psychology,space,nature"
).split(",")


# ─────────────────────────────────────────────
# 1. Google Trends via RSS (reliable, no library)
# ─────────────────────────────────────────────
def get_google_trends():
    topics = []
    headers = {"User-Agent": "Mozilla/5.0 (compatible; ContentBot/1.0)"}

    try:
        # Google Trends daily RSS feed
        r = requests.get(
            "https://trends.google.com/trending/rss?geo=US",
            headers=headers, timeout=12
        )
        soup = BeautifulSoup(r.content, "xml")
        for item in soup.find_all("item")[:20]:
            title = item.find("title")
            if title:
                text = title.get_text(strip=True)
                if len(text) > 3:
                    topics.append({
                        "topic": text,
                        "source": "google_trends_rss",
                        "score": 82
                    })
        print("    Google Trends RSS: " + str(len(topics)) + " topics")
    except Exception as e:
        print("    Google Trends RSS: skipped (" + str(e) + ")")

    return topics


# ─────────────────────────────────────────────
# 2. Reddit public JSON (no API key)
# ─────────────────────────────────────────────
def get_reddit_trends():
    topics = []
    subreddits = [
        "todayilearned", "interestingasfuck", "Damnthatsinteresting",
        "science", "history", "space", "psychology", "mildlyinteresting",
        "technology", "educationalgifs", "explainlikeimfive", "woahdude",
        "natureisfuckinglit", "engineering"
    ]
    headers = {"User-Agent": "Mozilla/5.0 (compatible; ContentBot/1.0)"}
    skip_words = ["me irl", "meme", "DAE ", "CMV:", "AITA", "unpopular opinion"]

    for sub in subreddits:
        try:
            r = requests.get(
                "https://www.reddit.com/r/" + sub + "/hot.json?limit=8",
                headers=headers, timeout=12
            )
            if r.status_code != 200:
                continue
            posts = r.json().get("data", {}).get("children", [])
            for post in posts:
                p = post["data"]
                upvotes = p.get("ups", 0)
                title = p.get("title", "").strip()
                if upvotes < 500 or len(title) < 15:
                    continue
                if any(w.lower() in title.lower() for w in skip_words):
                    continue
                score = min(95, 50 + int(upvotes / 1000) * 5)
                # Clean HN prefixes
                title = re.sub(r"^(Show HN:|Ask HN:|Tell HN:)\s*", "", title).strip()
                if len(title) < 10:
                    continue
                topics.append({
                    "topic": title,
                    "source": "reddit_r/" + sub,
                    "score": score,
                    "upvotes": upvotes
                })
            time.sleep(0.8)
        except Exception:
            continue

    print("    Reddit: " + str(len(topics)) + " topics")
    return topics


# ─────────────────────────────────────────────
# 3. Wikipedia curiosities
# ─────────────────────────────────────────────
def get_wikipedia_curiosities():
    topics = []
    headers = {"User-Agent": "Mozilla/5.0 (compatible; ContentBot/1.0)"}
    skip_prefixes = ("Wikipedia:", "Category:", "Template:", "Help:", "wikt:", "File:", "Portal:")

    try:
        r = requests.get("https://en.wikipedia.org/wiki/Main_Page", headers=headers, timeout=12)
        soup = BeautifulSoup(r.content, "html.parser")
        for div_id, source in [("mp-dyk", "wikipedia_dyk"), ("mp-otd", "wikipedia_otd")]:
            section = soup.find("div", {"id": div_id})
            if section:
                for li in section.find_all("li")[:8]:
                    text = li.get_text(strip=True)
                    if len(text) > 25 and len(text.split()) >= 5:
                        topics.append({"topic": text[:150], "source": source, "score": 65})
    except Exception as e:
        print("    Wikipedia main: " + str(e))

    try:
        r = requests.get(
            "https://en.wikipedia.org/wiki/Wikipedia:Unusual_articles",
            headers=headers, timeout=12
        )
        soup = BeautifulSoup(r.content, "html.parser")
        content = soup.find("div", {"id": "mw-content-text"})
        if content:
            for a in content.find_all("a", href=True)[:40]:
                title = a.get("title", "").strip()
                if (title and len(title) > 10
                        and not any(title.startswith(p) for p in skip_prefixes)
                        and len(title.split()) >= 3):
                    topics.append({
                        "topic": "The strange truth about: " + title,
                        "source": "wikipedia_unusual",
                        "score": 70
                    })
    except Exception:
        pass

    print("    Wikipedia: " + str(len(topics)) + " topics")
    return topics


# ─────────────────────────────────────────────
# 4. HackerNews (filtered)
# ─────────────────────────────────────────────
def get_hackernews_trends():
    topics = []
    skip_keywords = [
        "emacs", "vim", "linux kernel", "compiler", "css framework",
        "react", "rust lang", "golang", "llvm", "parser", "regex",
        "sql", "docker", "kubernetes", "devops", "cli tool",
        "package manager", "git", "github actions", "javascript library"
    ]
    try:
        r = requests.get(
            "https://hacker-news.firebaseio.com/v0/topstories.json",
            timeout=10
        )
        for sid in r.json()[:30]:
            try:
                story = requests.get(
                    "https://hacker-news.firebaseio.com/v0/item/" + str(sid) + ".json",
                    timeout=5
                ).json()
                title = story.get("title", "")
                score = story.get("score", 0)
                if score < 100 or not title:
                    continue
                if any(kw in title.lower() for kw in skip_keywords):
                    continue
                # Clean HN prefixes
                title = re.sub(r"^(Show HN:|Ask HN:|Tell HN:)\s*", "", title).strip()
                if len(title) < 10:
                    continue
                topics.append({
                    "topic": title,
                    "source": "hackernews",
                    "score": min(85, int(score / 8))
                })
                time.sleep(0.2)
            except Exception:
                continue
    except Exception as e:
        print("    HackerNews error: " + str(e))
    print("    HackerNews: " + str(len(topics)) + " topics")
    return topics


# ─────────────────────────────────────────────
# 5. RSS feeds (science/history news)
# ─────────────────────────────────────────────
def get_rss_topics():
    topics = []
    feeds = [
        ("https://feeds.bbci.co.uk/news/science_and_environment/rss.xml", "BBC Science"),
        ("https://www.sciencedaily.com/rss/top/science.xml", "ScienceDaily"),
        ("https://www.livescience.com/feeds/all", "LiveScience"),
    ]
    headers = {"User-Agent": "Mozilla/5.0 (compatible; ContentBot/1.0)"}
    for url, source_name in feeds:
        try:
            r = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(r.content, "xml")
            for item in soup.find_all("item")[:6]:
                title = item.find("title")
                if title:
                    text = title.get_text(strip=True)
                    if len(text) > 15:
                        topics.append({"topic": text, "source": source_name, "score": 72})
            time.sleep(0.5)
        except Exception:
            continue
    print("    RSS feeds: " + str(len(topics)) + " topics")
    return topics


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
def scan_all_trends():
    print("\n Scanning trends...")
    all_topics = []

    print("  -> Google Trends RSS...")
    all_topics += get_google_trends()
    print("  -> Reddit...")
    all_topics += get_reddit_trends()
    print("  -> Wikipedia...")
    all_topics += get_wikipedia_curiosities()
    print("  -> HackerNews...")
    all_topics += get_hackernews_trends()
    print("  -> RSS Feeds...")
    all_topics += get_rss_topics()

    seen = set()
    unique = []
    for t in all_topics:
        key = t["topic"][:35].lower().strip()
        if key not in seen and len(t["topic"]) > 10:
            seen.add(key)
            unique.append(t)

    unique.sort(key=lambda x: x["score"], reverse=True)

    cache = {"timestamp": datetime.now().isoformat(), "topics": unique[:60]}
    with open("topics_cache.json", "w") as f:
        json.dump(cache, f, indent=2)

    print("\n  " + str(len(unique)) + " unique topics saved")
    return unique[:60]


if __name__ == "__main__":
    topics = scan_all_trends()
    print("\nTop 15 topics:")
    for i, t in enumerate(topics[:15], 1):
        print("  " + str(i) + ". [" + str(t["score"]) + "] " + t["topic"][:70] + " (" + t["source"] + ")")
