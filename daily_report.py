"""
daily_report.py
───────────────
Runs every morning at 8AM via cron.
Sends a daily niche briefing to Telegram:
  - What went viral yesterday in your niches
  - Emerging trends to jump on early
  - Top 3 recommended videos to make today
  - Best posting time for today
"""

import json
import os
import requests
import time
from datetime import datetime
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
NICHE_KEYWORDS = os.getenv(
    "NICHE_KEYWORDS",
    "engineering,science,history,technology,psychology,space,nature"
).split(",")


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────
def send(text):
    if not BOT_TOKEN:
        print(text)
        return
    chunks = [text[i:i+4000] for i in range(0, len(text), 4000)]
    for chunk in chunks:
        try:
            requests.post(
                "https://api.telegram.org/bot" + BOT_TOKEN + "/sendMessage",
                json={"chat_id": CHAT_ID, "text": chunk, "disable_web_page_preview": True},
                timeout=15
            )
            time.sleep(0.3)
        except Exception as e:
            print("[Send error] " + str(e))


def ask_groq(prompt, max_tokens=1000):
    if not GROQ_API_KEY:
        return None
    try:
        r = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": "Bearer " + GROQ_API_KEY,
                "Content-Type": "application/json"
            },
            json={
                "model": "llama-3.1-8b-instant",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.7,
                "max_tokens": max_tokens
            },
            timeout=30
        )
        if r.status_code == 200:
            return r.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print("[Groq] " + str(e))
    return None


# ─────────────────────────────────────────────
# 1. What went viral yesterday on Reddit
# ─────────────────────────────────────────────
def get_yesterdays_viral():
    viral = []
    subreddits = [
        "todayilearned", "interestingasfuck", "Damnthatsinteresting",
        "science", "history", "space", "psychology", "technology"
    ]
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}

    for sub in subreddits:
        try:
            r = requests.get(
                "https://www.reddit.com/r/" + sub + "/top.json?t=day&limit=3",
                headers=headers, timeout=10
            )
            if r.status_code != 200:
                continue
            posts = r.json().get("data", {}).get("children", [])
            for post in posts:
                p = post["data"]
                upvotes = p.get("ups", 0)
                title = p.get("title", "").strip()
                comments = p.get("num_comments", 0)
                if upvotes > 500 and len(title) > 15:
                    viral.append({
                        "title": title,
                        "upvotes": upvotes,
                        "comments": comments,
                        "subreddit": sub
                    })
            time.sleep(0.5)
        except Exception:
            continue

    viral.sort(key=lambda x: x["upvotes"], reverse=True)

    # Fallback: if Reddit blocked, use cached trends from last scan
    if not viral:
        print("  Reddit blocked - using cached trends as fallback")
        try:
            import json
            with open("topics_cache.json") as f:
                cache = json.load(f)
            for t in cache.get("topics", [])[:15]:
                if t.get("score", 0) >= 60:
                    viral.append({
                        "title": t["topic"][:100],
                        "upvotes": t.get("score", 60) * 10,
                        "comments": 0,
                        "subreddit": t.get("source", "cache")
                    })
        except Exception:
            pass

    return viral[:15]


# ─────────────────────────────────────────────
# 2. Emerging trends via Google Trends RSS + news
# ─────────────────────────────────────────────
def get_emerging_trends():
    trends = []
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}

    # Google Trends RSS (reliable, no library needed)
    try:
        r = requests.get(
            "https://trends.google.com/trending/rss?geo=US",
            headers=headers, timeout=12
        )
        soup = BeautifulSoup(r.content, "xml")
        for item in soup.find_all("item")[:15]:
            title = item.find("title")
            if title:
                trends.append(title.get_text(strip=True))
        print("  Google Trends RSS: " + str(len(trends)) + " trends")
    except Exception as e:
        print("  Google Trends RSS: skipped (" + str(e) + ")")

    # Science/history RSS feeds
    feeds = [
        "https://feeds.bbci.co.uk/news/science_and_environment/rss.xml",
        "https://www.sciencedaily.com/rss/top/science.xml",
        "https://www.livescience.com/feeds/all",
    ]
    for feed_url in feeds:
        try:
            r = requests.get(feed_url, headers=headers, timeout=8)
            soup = BeautifulSoup(r.content, "xml")
            for item in soup.find_all("item")[:4]:
                title = item.find("title")
                if title:
                    trends.append(title.get_text(strip=True))
            time.sleep(0.3)
        except Exception:
            pass

    return trends[:25]


# ─────────────────────────────────────────────
# 3. Best posting time for today
# ─────────────────────────────────────────────
def get_best_posting_time():
    day = datetime.now().strftime("%A")
    # (US Eastern Time, Singapore Time SGT=ET+13h, skip_for_sg flag)
    schedule = {
        "Monday":    [("7:00 AM",  "7:30 PM MMT",  False), ("12:00 PM", "12:30 AM MMT", True),  ("7:00 PM",  "7:30 AM MMT",  False)],
        "Tuesday":   [("9:00 AM",  "9:30 PM MMT",  False), ("2:00 PM",  "2:30 AM MMT",  True),  ("8:00 PM",  "8:30 AM MMT",  False)],
        "Wednesday": [("7:00 AM",  "7:30 PM MMT",  False), ("11:00 AM", "11:30 PM MMT", False), ("7:00 PM",  "7:30 AM MMT",  False)],
        "Thursday":  [("9:00 AM",  "9:30 PM MMT",  False), ("12:00 PM", "12:30 AM MMT", True),  ("7:00 PM",  "7:30 AM MMT",  False)],
        "Friday":    [("5:00 AM",  "5:30 PM MMT",  False), ("1:00 PM",  "1:30 AM MMT",  True),  ("3:00 PM",  "3:30 AM MMT",  True)],
        "Saturday":  [("11:00 AM", "11:30 PM MMT", False), ("7:00 PM",  "7:30 AM MMT",  False), ("8:00 PM",  "8:30 AM MMT",  False)],
        "Sunday":    [("7:00 AM",  "7:30 PM MMT",  False), ("8:00 AM",  "8:30 PM MMT",  False), ("4:00 PM",  "4:30 AM MMT",  True)],
    }
    slots = schedule.get(day, [("9:00 AM", "9:30 PM MMT", False), ("12:00 PM", "12:30 AM MMT", True), ("7:00 PM", "7:30 AM MMT", False)])
    return day, slots


# ─────────────────────────────────────────────
# 4. AI recommendations
# ─────────────────────────────────────────────
def generate_recommendations(viral_posts, emerging_trends):
    viral_text = "\n".join([
        str(i+1) + ". " + p["title"] + " (" + str(p["upvotes"]) + " upvotes, r/" + p["subreddit"] + ")"
        for i, p in enumerate(viral_posts[:10])
    ])
    trends_text = "\n".join([str(i+1) + ". " + t for i, t in enumerate(emerging_trends[:10])])

    prompt = (
        "You are a viral content strategist. Use ONLY the real data provided below. Do not make up topics or people. Recommend 3 videos based strictly on what appears in the lists below.\n\n"
        "recommend the 3 best videos to make TODAY.\n\n"
        "WHAT WENT VIRAL YESTERDAY ON REDDIT:\n" + viral_text + "\n\n"
        "EMERGING GOOGLE TRENDS:\n" + trends_text + "\n\n"
        "Pick the 3 BEST opportunities for a creator focused on: " + ", ".join(NICHE_KEYWORDS) + "\n\nIMPORTANT: Give exactly 3 videos total, not 3 per category. Just the top 3 overall.\n\n"
        "For each:\n\n"
        "VIDEO 1:\n"
        "Topic: [specific topic]\n"
        "Why now: [why post this today]\n"
        "Angle: [specific viral angle]\n"
        "Hook: [exact first sentence]\n"
        "Urgency: HIGH, MEDIUM, or LOW\n\n"
        "VIDEO 2:\n"
        "Topic: [specific topic]\n"
        "Why now: [why post this today]\n"
        "Angle: [specific viral angle]\n"
        "Hook: [exact first sentence]\n"
        "Urgency: HIGH, MEDIUM, or LOW\n\n"
        "VIDEO 3:\n"
        "Topic: [specific topic]\n"
        "Why now: [why post this today]\n"
        "Angle: [specific viral angle]\n"
        "Hook: [exact first sentence]\n"
        "Urgency: HIGH, MEDIUM, or LOW\n\n"
        "TREND TO WATCH: one topic that could explode in 48 hours"
    )
    return ask_groq(prompt, max_tokens=900)


# ─────────────────────────────────────────────
# 5. Niche activity summary
# ─────────────────────────────────────────────
def get_niche_summary(viral_posts):
    niche_map = {
        "todayilearned": "general", "interestingasfuck": "general",
        "Damnthatsinteresting": "general", "science": "science",
        "history": "history", "space": "science",
        "psychology": "psychology", "technology": "technology"
    }
    counts = {}
    for post in viral_posts:
        niche = niche_map.get(post["subreddit"], "general")
        counts[niche] = counts.get(niche, 0) + 1
    return sorted(counts.items(), key=lambda x: x[1], reverse=True)


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
def send_daily_report():
    today = datetime.now().strftime("%A, %B %d")
    print("[" + datetime.now().strftime("%H:%M") + "] Generating daily report for " + today)

    send("Good morning! Generating your daily content briefing...")

    print("  Fetching viral posts...")
    viral = get_yesterdays_viral()

    print("  Fetching emerging trends...")
    trends = get_emerging_trends()

    print("  Generating AI recommendations...")
    recommendations = generate_recommendations(viral, trends)

    day, posting_times = get_best_posting_time()
    niche_summary = get_niche_summary(viral)

    # Header + niche activity
    msg = "DAILY BRIEFING - " + today + "\n"
    msg += "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    msg += "NICHE ACTIVITY YESTERDAY\n"
    for niche, count in niche_summary[:4]:
        bar = "█" * count + "░" * (5 - min(count, 5))
        msg += "  " + niche.upper() + ": " + bar + " (" + str(count) + " viral posts)\n"
    msg += "\n"

    # Top viral posts
    msg += "TOP VIRAL POSTS YESTERDAY\n"
    for i, post in enumerate(viral[:5], 1):
        msg += str(i) + ". " + post["title"][:70] + "\n"
        msg += "   " + str(post["upvotes"]) + " upvotes | " + str(post["comments"]) + " comments | r/" + post["subreddit"] + "\n"

    send(msg)

    # AI recommendations
    if recommendations:
        rec_msg = "TODAY'S TOP 3 VIDEO RECOMMENDATIONS\n"
        rec_msg += "━━━━━━━━━━━━━━━━━━━━━━━━\n"
        rec_msg += recommendations
        send(rec_msg)
    else:
        send("Could not generate AI recommendations today.")

    # Posting schedule
    schedule_msg = "━━━━━━━━━━━━━━━━━━━━━━━━\n"
    schedule_msg += "BEST POSTING TIMES TODAY (" + day + ")\n"
    for i, (et, mmt, skip) in enumerate(posting_times, 1):
        flag = " (skip - too late)" if skip else " RECOMMENDED"
        schedule_msg += "  Slot " + str(i) + ": " + et + " ET  =  " + mmt + flag + "\n"
    schedule_msg += "\n"
    schedule_msg += "QUICK ACTIONS:\n"
    schedule_msg += "  hooks <topic>   - test 5 hooks\n"
    schedule_msg += "  score <topic>   - viral score\n"
    schedule_msg += "  series <topic>  - 5-part series\n"
    schedule_msg += "  scan            - get fresh trends"
    send(schedule_msg)

    print("  Daily report sent!")


if __name__ == "__main__":
    send_daily_report()
