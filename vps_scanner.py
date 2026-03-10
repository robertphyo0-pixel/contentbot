"""
vps_scanner.py
──────────────
Runs on VPS 24/7 every 6 hours.
Scans trends, analyzes angles, sends full report to Telegram.
No AI needed — pure trend research only.
"""

import json
import time
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# ─────────────────────────────────────────────
# Import our existing modules
# ─────────────────────────────────────────────
from trend_scanner import scan_all_trends
from topic_analyzer import analyze_topics
from telegram_sender import send_message


# ─────────────────────────────────────────────
# Format full Telegram report
# ─────────────────────────────────────────────
def format_alert(angles, topics):
    now = datetime.now().strftime("%A %b %d, %H:%M")

    # Header
    msg = f"""🔥 *TREND ALERT* — {now}
━━━━━━━━━━━━━━━━━━━━━━━━
Found *{len(angles)} video angles* from *{len(topics)} trending topics*
━━━━━━━━━━━━━━━━━━━━━━━━

"""

    # Group angles by niche
    niches = {}
    for a in angles:
        niche = a.get("niche", "general")
        if niche not in niches:
            niches[niche] = []
        niches[niche].append(a)

    # Print each niche group
    niche_icons = {
        "engineering": "⚙️",
        "history": "🏛",
        "science": "🔬",
        "psychology": "🧠",
        "technology": "💻",
        "general": "🌍"
    }

    for niche, niche_angles in niches.items():
        icon = niche_icons.get(niche, "📌")
        msg += f"{icon} *{niche.upper()}*\n"
        for a in niche_angles[:5]:  # top 5 per niche
            score = a.get("virality_score", 0)
            angle = a.get("angle", "")
            source = a.get("source_topic", "")[:50]
            msg += f"  • [{score}/100] {angle}\n"
            msg += f"    _Source: {source}_\n"
        msg += "\n"

    # Top 3 picks
    top3 = sorted(angles, key=lambda x: x["virality_score"], reverse=True)[:3]
    msg += "━━━━━━━━━━━━━━━━━━━━━━━━\n"
    msg += "⭐ *TOP 3 TO PRODUCE NOW*\n"
    msg += "━━━━━━━━━━━━━━━━━━━━━━━━\n"
    for i, a in enumerate(top3, 1):
        msg += f"{i}. [{a['virality_score']}/100] {a['angle']}\n"

    msg += "\n💡 _Run on your Mac to generate full scripts:_\n"
    msg += "`python3 mac_generator.py`"

    return msg


# ─────────────────────────────────────────────
# Main scan + alert loop
# ─────────────────────────────────────────────
def run_scan():
    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M')}] Starting scan...")

    # Step 1: Scan trends
    topics = scan_all_trends()
    if not topics:
        print("No topics found, skipping alert.")
        return

    # Step 2: Analyze angles
    angles = analyze_topics(topics)
    if not angles:
        print("No angles generated, skipping alert.")
        return

    # Step 3: Save for Mac to pick up
    cache = {
        "timestamp": datetime.now().isoformat(),
        "topics": topics,
        "angles": angles
    }
    with open("latest_trends.json", "w") as f:
        json.dump(cache, f, indent=2)

    print(f"Saved {len(angles)} angles to latest_trends.json")

    # Step 4: Send Telegram alert
    msg = format_alert(angles, topics)
    success = send_message(msg)

    if success:
        print(f"✅ Alert sent to Telegram ({len(angles)} angles)")
    else:
        print("❌ Telegram send failed")


# ─────────────────────────────────────────────
# Run once immediately, then every 6 hours
# ─────────────────────────────────────────────
if __name__ == "__main__":
    print("🚀 VPS Scanner started — runs every 6 hours")
    print("   Press Ctrl+C to stop\n")

    while True:
        try:
            run_scan()
        except Exception as e:
            print(f"❌ Scan error: {e}")

        # Wait 6 hours
        next_run = datetime.now().strftime("%H:%M")
        print(f"💤 Next scan in 6 hours... (started at {next_run})")
        time.sleep(6 * 60 * 60)
