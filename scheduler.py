"""
scheduler.py
────────────
Main pipeline orchestrator.
Runs the full content bot workflow:
  trend_scanner → topic_analyzer → video_plan_generator → telegram_sender

Can be run manually or via cron.
"""

import os
import sys
import json
import logging
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# ─────────────────────────────────────────────
# Logging
# ─────────────────────────────────────────────
os.makedirs("logs", exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("logs/bot.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
log = logging.getLogger("ContentBot")


# ─────────────────────────────────────────────
# Pipeline steps
# ─────────────────────────────────────────────
def step_scan_trends():
    log.info("━━━ STEP 1: Scanning Trends ━━━")
    try:
        from trend_scanner import scan_all_trends
        topics = scan_all_trends()
        log.info(f"✅ Found {len(topics)} trending topics")
        return topics
    except Exception as e:
        log.error(f"❌ Trend scan failed: {e}")
        return []


def step_analyze_topics(topics):
    log.info("━━━ STEP 2: Analyzing Topics ━━━")
    try:
        from topic_analyzer import analyze_topics
        angles = analyze_topics(topics)
        log.info(f"✅ Generated {len(angles)} video angles")
        return angles
    except Exception as e:
        log.error(f"❌ Topic analysis failed: {e}")
        return []


def step_generate_plans(angles):
    log.info("━━━ STEP 3: Generating Video Plans ━━━")
    try:
        from video_plan_generator import generate_weekly_plans
        plans = generate_weekly_plans(angles)
        log.info(f"✅ Generated {len(plans)} video plans")
        return plans
    except Exception as e:
        log.error(f"❌ Plan generation failed: {e}")
        return []


def step_send_telegram(plans):
    log.info("━━━ STEP 4: Sending to Telegram ━━━")
    try:
        from telegram_sender import send_weekly_pack
        result = send_weekly_pack(plans)
        if result:
            log.info("✅ Weekly pack delivered to Telegram")
        else:
            log.warning("⚠️  Telegram send had issues (check config)")
        return result
    except Exception as e:
        log.error(f"❌ Telegram send failed: {e}")
        return False


def save_run_log(status, topics_found, angles_found, plans_generated):
    """Save a run summary to track history."""
    run = {
        "timestamp": datetime.now().isoformat(),
        "status": status,
        "topics_found": topics_found,
        "angles_found": angles_found,
        "plans_generated": plans_generated
    }

    log_file = "logs/runs.json"
    history = []
    try:
        with open(log_file) as f:
            history = json.load(f)
    except Exception:
        pass

    history.append(run)
    history = history[-52:]  # Keep 1 year of weekly runs

    with open(log_file, "w") as f:
        json.dump(history, f, indent=2)


# ─────────────────────────────────────────────
# MAIN PIPELINE
# ─────────────────────────────────────────────
def run_pipeline():
    start = datetime.now()

    log.info("╔══════════════════════════════════════╗")
    log.info("║  CONTENT BOT - WEEKLY PIPELINE       ║")
    log.info(f"║  {start.strftime('%A %B %d, %Y %H:%M')}           ║")
    log.info("╚══════════════════════════════════════╝")

    # Run pipeline
    topics = step_scan_trends()
    if not topics:
        log.warning("No topics found — will still try with empty cache")

    angles = step_analyze_topics(topics)
    if not angles:
        log.error("No angles generated. Check topic analyzer.")
        save_run_log("failed", len(topics), 0, 0)
        return

    plans = step_generate_plans(angles)
    if not plans:
        log.error("No plans generated. Check Ollama is running.")
        save_run_log("failed", len(topics), len(angles), 0)
        return

    step_send_telegram(plans)

    duration = (datetime.now() - start).seconds
    log.info(f"\n✅ Pipeline complete in {duration//60}m {duration%60}s")
    log.info(f"   Topics: {len(topics)} | Angles: {len(angles)} | Plans: {len(plans)}")

    save_run_log("success", len(topics), len(angles), len(plans))


# ─────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────
if __name__ == "__main__":
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == "scan":
            step_scan_trends()
        elif cmd == "analyze":
            step_analyze_topics(None)
        elif cmd == "generate":
            step_generate_plans(None)
        elif cmd == "send":
            step_send_telegram(None)
        elif cmd == "status":
            # Show last run stats
            try:
                with open("logs/runs.json") as f:
                    runs = json.load(f)
                last = runs[-1]
                print(f"\nLast run: {last['timestamp']}")
                print(f"Status:   {last['status']}")
                print(f"Topics:   {last['topics_found']}")
                print(f"Angles:   {last['angles_found']}")
                print(f"Plans:    {last['plans_generated']}")
            except Exception:
                print("No run history found.")
        else:
            print(f"Unknown command: {cmd}")
            print("Usage: python3 scheduler.py [scan|analyze|generate|send|status]")
    else:
        run_pipeline()
