"""
test_run.py
───────────
Run this FIRST to verify your setup works before waiting for Sunday.
Tests each component individually and shows you what the output looks like.
"""

import sys
import json
import os
from dotenv import load_dotenv

load_dotenv()

def test_ollama():
    print("\n[1/4] Testing Ollama connection...")
    try:
        import requests
        r = requests.get("http://localhost:11434/api/tags", timeout=5)
        if r.status_code == 200:
            models = [m["name"] for m in r.json().get("models", [])]
            print(f"  ✅ Ollama running. Models available: {models}")
            return True
        else:
            print(f"  ❌ Ollama returned {r.status_code}")
            return False
    except Exception as e:
        print(f"  ❌ Ollama not running: {e}")
        print(f"     Fix: run 'ollama serve' in a separate terminal")
        return False


def test_trend_scanner():
    print("\n[2/4] Testing trend scanner (quick scan)...")
    try:
        from trend_scanner import get_wikipedia_curiosities, get_hackernews_trends
        wiki = get_wikipedia_curiosities()
        hn = get_hackernews_trends()
        all_topics = wiki + hn
        print(f"  ✅ Got {len(wiki)} Wikipedia + {len(hn)} HackerNews topics")
        if all_topics:
            print(f"  Sample: {all_topics[0]['topic'][:70]}")
        return all_topics
    except Exception as e:
        print(f"  ❌ Trend scanner error: {e}")
        return []


def test_topic_analyzer(topics):
    print("\n[3/4] Testing topic analyzer...")
    try:
        from topic_analyzer import analyze_topics, generate_angles, detect_niche
        if not topics:
            # Use dummy data
            topics = [
                {"topic": "airport security hidden cameras", "source": "test", "score": 80},
                {"topic": "ancient Roman concrete mystery", "source": "test", "score": 75},
                {"topic": "how black holes actually work", "source": "test", "score": 85},
            ]
        angles = analyze_topics(topics)
        print(f"  ✅ Generated {len(angles)} video angles")
        if angles:
            a = angles[0]
            print(f"  Best angle: [{a['virality_score']}] {a['angle']}")
        return angles
    except Exception as e:
        print(f"  ❌ Analyzer error: {e}")
        return []


def test_single_video_plan(angles):
    print("\n[4/4] Testing video plan generation (1 video)...")
    if not angles:
        print("  ⚠️  No angles available, using sample topic...")
        angles = [{
            "angle": "The hidden engineering detail in airplane windows",
            "niche": "engineering",
            "virality_score": 88,
            "source_topic": "airplane window hole"
        }]

    try:
        from video_plan_generator import call_ollama, build_video_prompt, parse_video_plan

        angle = angles[0]
        print(f"  Generating plan for: {angle['angle'][:60]}...")

        prompt = build_video_prompt(angle)
        raw = call_ollama(prompt)

        if raw:
            plan = parse_video_plan(raw, angle)
            print(f"  ✅ Video plan generated!")
            print(f"\n  ┌─ PREVIEW ──────────────────────────────────")
            print(f"  │ TITLE:  {plan.get('title', 'N/A')}")
            print(f"  │ HOOK:   {plan.get('hook', 'N/A')[:80]}")
            print(f"  │ SCRIPT: {plan.get('script', 'N/A')[:100]}...")
            print(f"  │ TAGS:   {' '.join(plan.get('hashtags', [])[:5])}")
            print(f"  └───────────────────────────────────────────")
            return True
        else:
            print(f"  ❌ Ollama returned empty response")
            print(f"     Try: ollama pull mistral")
            return False

    except Exception as e:
        print(f"  ❌ Plan generation error: {e}")
        return False


def test_telegram():
    print("\n[Bonus] Testing Telegram...")
    token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    if not token or token == "your_bot_token_here":
        print("  ⚠️  Telegram not configured in .env — skip for now")
        print("     Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID when ready")
        return

    try:
        from telegram_sender import test_telegram as tg_test
        tg_test()
    except Exception as e:
        print(f"  ❌ Telegram error: {e}")


def show_setup_instructions():
    print("""
╔══════════════════════════════════════════════════════╗
║           SETUP INSTRUCTIONS                         ║
╠══════════════════════════════════════════════════════╣
║                                                      ║
║  1. TELEGRAM BOT SETUP (5 min)                       ║
║     • Open Telegram → search @BotFather              ║
║     • Send: /newbot                                  ║
║     • Name it anything, get TOKEN                    ║
║     • Open your bot → send any message               ║
║     • Get Chat ID:                                   ║
║       curl "https://api.telegram.org/bot<TOKEN>/     ║
║             getUpdates"                              ║
║     • Add TOKEN and CHAT_ID to .env                  ║
║                                                      ║
║  2. CRON JOB (auto-run every Sunday 9AM)             ║
║     crontab -e                                       ║
║     Add: 0 9 * * 0 cd ~/content-bot &&              ║
║          source venv/bin/activate &&                 ║
║          python3 scheduler.py >> logs/cron.log 2>&1  ║
║                                                      ║
║  3. RUN MANUALLY ANYTIME                             ║
║     python3 scheduler.py                             ║
║                                                      ║
╚══════════════════════════════════════════════════════╝
    """)


# ─── MAIN ─────────────────────────────────────
if __name__ == "__main__":
    print("╔══════════════════════════════════════╗")
    print("║  CONTENT BOT - SYSTEM TEST           ║")
    print("╚══════════════════════════════════════╝")

    results = {}

    results["ollama"] = test_ollama()

    if results["ollama"]:
        topics = test_trend_scanner()
        angles = test_topic_analyzer(topics)
        results["video_plan"] = test_single_video_plan(angles)
    else:
        print("\n  ⚠️  Ollama not running — skipping AI tests")
        print("  Run: ollama serve (in background)")
        topics = test_trend_scanner()
        angles = test_topic_analyzer(topics)

    test_telegram()

    print("\n╔══════════════════════════════════════╗")
    print("║  TEST SUMMARY                         ║")
    print("╠══════════════════════════════════════╣")
    for k, v in results.items():
        status = "✅" if v else "❌"
        print(f"║  {status} {k:<30}        ║")
    print("╚══════════════════════════════════════╝")

    show_setup_instructions()
