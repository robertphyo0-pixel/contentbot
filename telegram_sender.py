"""
telegram_sender.py
──────────────────
Formats and sends the weekly content pack to your Telegram.
Splits long messages automatically (Telegram 4096 char limit).
Sends each video as its own message for readability.
"""

import json
import requests
import os
import time
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")


# ─────────────────────────────────────────────
# Core Telegram API
# ─────────────────────────────────────────────
def send_message(text, parse_mode="Markdown"):
    """Send a message to Telegram. Splits if over 4096 chars."""
    if not BOT_TOKEN or BOT_TOKEN == "your_bot_token_here":
        print("  ⚠️  Telegram not configured. Check .env file.")
        print(f"  [TELEGRAM PREVIEW]\n{text[:300]}...")
        return False

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    # Split long messages
    chunks = split_message(text, 4000)

    success = True
    for chunk in chunks:
        payload = {
            "chat_id": CHAT_ID,
            "text": chunk,
            "parse_mode": parse_mode,
            "disable_web_page_preview": True
        }
        try:
            r = requests.post(url, json=payload, timeout=15)
            if r.status_code != 200:
                print(f"  [Telegram] Error: {r.json()}")
                success = False
        except Exception as e:
            print(f"  [Telegram] Send failed: {e}")
            success = False

        time.sleep(0.5)  # Rate limit

    return success


def split_message(text, max_len=4000):
    """Split text into chunks, breaking at newlines when possible."""
    if len(text) <= max_len:
        return [text]

    chunks = []
    while len(text) > max_len:
        # Find last newline before max_len
        split_at = text.rfind("\n", 0, max_len)
        if split_at == -1:
            split_at = max_len
        chunks.append(text[:split_at])
        text = text[split_at:].lstrip("\n")

    if text:
        chunks.append(text)

    return chunks


# ─────────────────────────────────────────────
# Message Formatters
# ─────────────────────────────────────────────
def format_weekly_header(week_label, total_videos):
    return f"""🎬 *WEEKLY CONTENT PACK*
📅 {week_label}
━━━━━━━━━━━━━━━━━━━━━━━━

This week: *{total_videos} ready-to-produce videos*
Each video: 25-35 seconds | TikTok + YouTube Shorts

Tap each plan below to copy scripts and prompts 👇"""


def format_video_plan(plan, index):
    """Format a single video plan as a Telegram message."""

    title = plan.get("title", "Untitled")
    hook = plan.get("hook", "N/A")
    voice = plan.get("voice_style", "N/A")
    script = plan.get("script", "N/A")
    scenes = plan.get("scenes", [])
    image_prompts = plan.get("image_prompts", [])
    editing = plan.get("editing", "N/A")
    caption = plan.get("caption", "N/A")
    hashtags = plan.get("hashtags", [])
    thumbnail = plan.get("thumbnail", "N/A")
    niche = plan.get("niche", "general")
    score = plan.get("virality_score", 0)

    # Scenes block
    scenes_text = ""
    for s in scenes[:5]:
        scenes_text += f"  • {s}\n"
    if not scenes_text:
        scenes_text = "  • (see raw script for scene details)\n"

    # Image prompts block
    prompts_text = ""
    for i, p in enumerate(image_prompts[:5], 1):
        prompts_text += f"  *{i}.* {p}\n\n"
    if not prompts_text:
        prompts_text = "  • (generate from scene descriptions)\n"

    # Hashtags
    hashtag_line = " ".join(hashtags[:12]) if hashtags else "#shorts #educational #viral"

    msg = f"""━━━━━━━━━━━━━━━━━━━━━━━━
🎥 *VIDEO {index}* | Niche: {niche.upper()} | Score: {score}/100
━━━━━━━━━━━━━━━━━━━━━━━━

📌 *TITLE*
{title}

⚡ *HOOK (First 3 seconds)*
_{hook}_

🎙 *VOICE STYLE*
{voice}

📝 *FULL SCRIPT*
{script}

🎬 *SCENE BREAKDOWN*
{scenes_text}
🖼 *AI IMAGE PROMPTS*
{prompts_text}
✂️ *EDITING NOTES*
{editing}

📱 *CAPTION*
{caption}

🏷 *HASHTAGS*
{hashtag_line}

🖼 *THUMBNAIL*
{thumbnail}
"""
    return msg


def format_production_checklist():
    return """━━━━━━━━━━━━━━━━━━━━━━━━
✅ *PRODUCTION CHECKLIST*
━━━━━━━━━━━━━━━━━━━━━━━━

Per video (15-25 min total):

☐ Generate 5 images using Leonardo AI / Midjourney
☐ Record voiceover in CapCut (AI voice or your own)
☐ Import images into CapCut vertical template
☐ Sync audio to scenes
☐ Add text overlays for hook and key facts
☐ Add subtle background music (low volume)
☐ Export 1080x1920 vertical
☐ Post on TikTok with caption + hashtags
☐ Upload same to YouTube Shorts

💡 *Pro tip:* Post TikTok first. If it performs well in 2hrs, push harder with Shorts.

🔁 *Next pack arrives Sunday 9AM automatically.*"""


# ─────────────────────────────────────────────
# MAIN: Send the weekly pack
# ─────────────────────────────────────────────
def send_weekly_pack(plans=None):
    """Load plans and send to Telegram."""

    if plans is None:
        try:
            with open("weekly_plans.json") as f:
                data = json.load(f)
            plans = data["plans"]
            week_label = data.get("week", datetime.now().strftime("%Y-W%W"))
        except FileNotFoundError:
            print("❌ weekly_plans.json not found. Run video_plan_generator.py first.")
            return False

    print(f"\n📲 Sending weekly pack to Telegram ({len(plans)} videos)...")

    # Message 1: Header
    header = format_weekly_header(week_label, len(plans))
    send_message(header)
    time.sleep(1)

    # One message per video
    for i, plan in enumerate(plans, 1):
        print(f"  Sending Video {i}...")
        msg = format_video_plan(plan, i)
        success = send_message(msg)
        if success:
            print(f"  ✅ Video {i} sent")
        else:
            print(f"  ❌ Video {i} failed")
        time.sleep(1.5)

    # Final: Production checklist
    checklist = format_production_checklist()
    send_message(checklist)

    print(f"\n✅ Weekly pack delivered! Check your Telegram.")
    return True


# ─────────────────────────────────────────────
# Test connection
# ─────────────────────────────────────────────
def test_telegram():
    msg = "✅ Content Bot connected! Your weekly video plans will arrive every Sunday at 9AM 🎬"
    result = send_message(msg)
    if result:
        print("✅ Telegram test successful!")
    else:
        print("❌ Telegram test failed. Check BOT_TOKEN and CHAT_ID in .env")
    return result


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        test_telegram()
    else:
        send_weekly_pack()
