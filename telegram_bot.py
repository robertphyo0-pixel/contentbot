"""
telegram_bot.py - Full Featured Content Bot
Commands:
  TRENDS:     scan, status, help
  GENERATE:   top3, all, 1 3 5, redo N
  NEW:        hooks <topic>, score <idea>, series <topic>, replies <comments>
"""

import json
import time
import os
import threading
import requests
import re
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
SCAN_INTERVAL_HOURS = 6

last_angles = []
last_scan_time = None
last_update_id = 0
is_generating = False


# ─────────────────────────────────────────────
# Telegram helpers
# ─────────────────────────────────────────────
def send(text):
    if not BOT_TOKEN:
        print(text[:100])
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


def get_updates():
    global last_update_id
    try:
        r = requests.get(
            "https://api.telegram.org/bot" + BOT_TOKEN + "/getUpdates",
            params={"offset": last_update_id + 1, "timeout": 30, "limit": 10},
            timeout=40
        )
        if r.status_code == 200:
            return r.json().get("result", [])
    except Exception:
        pass
    return []


# ─────────────────────────────────────────────
# Groq API helper
# ─────────────────────────────────────────────
def ask_groq(prompt, max_tokens=1200, temperature=0.85):
    if not GROQ_API_KEY:
        return None
    try:
        r = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": "Bearer " + GROQ_API_KEY, "Content-Type": "application/json"},
            json={
                "model": "llama-3.1-8b-instant",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": temperature,
                "max_tokens": max_tokens
            },
            timeout=30
        )
        if r.status_code == 200:
            return r.json()["choices"][0]["message"]["content"].strip()
        else:
            print("[Groq] Error " + str(r.status_code) + ": " + r.text[:200])
    except Exception as e:
        print("[Groq] " + str(e))
    return None


# ─────────────────────────────────────────────
# Topic quality filter
# ─────────────────────────────────────────────
JUNK_PATTERNS = [
    "wikt:", "Category:", "Template:", "Help:", "File:", "Portal:",
    "d.1", "d.2", "b.1", "b.2", "Airborne Observatory",
    "Wave Function Collapse", "Procedural Hex",
]

def is_quality_angle(angle):
    text = angle.get("angle", "")
    source = angle.get("source_topic", "")
    for p in JUNK_PATTERNS:
        if p.lower() in text.lower() or p.lower() in source.lower():
            return False
    if len(text.split()) < 4 or len(text.split()) > 15:
        return False
    if re.search(r'\d{4}', source):
        return False
    return True


# ─────────────────────────────────────────────
# Scan & trend alert
# ─────────────────────────────────────────────
def run_scan(silent=False):
    global last_angles, last_scan_time
    if not silent:
        send("Scanning trends now...")
    try:
        from trend_scanner import scan_all_trends
        from topic_analyzer import analyze_topics
        topics = scan_all_trends()
        angles = analyze_topics(topics)
        quality = [a for a in angles if is_quality_angle(a)]
        last_angles = quality if quality else angles
        last_scan_time = datetime.now()
        with open("latest_trends.json", "w") as f:
            json.dump({"timestamp": last_scan_time.isoformat(), "topics": topics, "angles": last_angles}, f, indent=2)
        send_trend_alert(last_angles, topics)
    except Exception as e:
        send("Scan error: " + str(e))


def send_trend_alert(angles, topics):
    now = datetime.now().strftime("%a %b %d, %H:%M")
    msg = "TREND ALERT - " + now + "\n"
    msg += str(len(angles)) + " video angles from " + str(len(topics)) + " topics\n\n"

    niches = {}
    for a in angles:
        n = a.get("niche", "general")
        niches.setdefault(n, []).append(a)

    niche_labels = {"engineering":"ENGINEERING","history":"HISTORY","science":"SCIENCE",
                    "psychology":"PSYCHOLOGY","technology":"TECHNOLOGY","general":"GENERAL"}

    idx = 1
    index_map = {}
    for niche, niche_angles in niches.items():
        msg += niche_labels.get(niche, niche.upper()) + "\n"
        for a in niche_angles[:4]:
            msg += "  " + str(idx) + ". [" + str(a.get("virality_score",0)) + "] " + a.get("angle","") + "\n"
            index_map[idx] = a
            idx += 1
        msg += "\n"

    with open("angle_index.json", "w") as f:
        json.dump({str(k): v for k, v in index_map.items()}, f, indent=2)

    msg += "GENERATE:\n"
    msg += "top3 / all / 1 3 5 / redo N\n\n"
    msg += "NEW TOOLS:\n"
    msg += "hooks <topic>   - 5 hooks ranked by virality\n"
    msg += "score <idea>    - viral score 1-100\n"
    msg += "series <topic>  - 5-part content series\n"
    msg += "replies         - generate comment replies"
    send(msg)


# ─────────────────────────────────────────────
# Video plan generator
# ─────────────────────────────────────────────
def generate_video_plan(angle, custom_angle=None):
    topic = custom_angle if custom_angle else angle["angle"]
    prompt = "You are a viral TikTok/YouTube Shorts expert scriptwriter. Your videos hit millions of views.\n\n"
    prompt += "Create a complete production plan for: " + topic + "\n\n"
    prompt += "Rules: Hook must be a REAL verified fact. Script 70-85 words. Never start with 'Did you know'.\n\n"
    prompt += "TITLE: catchy title under 60 chars\n\n"
    prompt += "HOOK: shocking verified first sentence\n\n"
    prompt += "SCRIPT: full 70-85 word narration ending with cliffhanger\n\n"
    prompt += "SCENE 1 (0-5s): exact visual\n"
    prompt += "SCENE 2 (5-11s): exact visual\n"
    prompt += "SCENE 3 (11-18s): exact visual\n"
    prompt += "SCENE 4 (18-25s): exact visual\n"
    prompt += "SCENE 5 (25-32s): exact visual\n\n"
    prompt += "IMAGE 1: [subject, camera angle, lighting, mood, style, ultra realistic, 8k]\n"
    prompt += "IMAGE 2: [subject, camera angle, lighting, mood, style, ultra realistic, 8k]\n"
    prompt += "IMAGE 3: [subject, camera angle, lighting, mood, style, ultra realistic, 8k]\n"
    prompt += "IMAGE 4: [subject, camera angle, lighting, mood, style, ultra realistic, 8k]\n"
    prompt += "IMAGE 5: [subject, camera angle, lighting, mood, style, ultra realistic, 8k]\n\n"
    prompt += "MUSIC: tempo, mood, genre, instruments, no lyrics\n"
    prompt += "EFFECTS: text overlays with exact timing, zoom punches, sound effects\n"
    prompt += "CAPTION: opens with shocking statement, ends with question, max 200 chars\n"
    prompt += "HASHTAGS: 12 hashtags mixing niche, broad, and trending"
    return ask_groq(prompt, max_tokens=1200)


def format_and_send_plan(angle, raw, index):
    msg = "VIDEO " + str(index) + " | " + angle.get("niche","general").upper()
    msg += " | Score: " + str(angle.get("virality_score",0)) + "/100\n"
    msg += "Topic: " + angle["angle"] + "\n"
    msg += "─────────────────────────\n"
    msg += raw
    msg += "\n─────────────────────────\n"
    msg += "FACT-CHECK REMINDER:\n"
    msg += "Verify all stats, hook claim, and dates on Google before filming.\n"
    msg += "Fake facts = audience trust lost forever."
    send(msg)


# ─────────────────────────────────────────────
# NEW TOOL 1: Hook A/B Tester
# ─────────────────────────────────────────────
def handle_hooks(topic):
    send("Generating 5 hooks for: " + topic + "...")

    prompt = (
        "You are a viral TikTok expert. Generate 5 completely different hooks for this topic:\n"
        "TOPIC: " + topic + "\n\n"
        "Rules:\n"
        "- Each hook is 1 sentence, max 20 words\n"
        "- Never start with 'Did you know'\n"
        "- Each uses a DIFFERENT psychological trigger\n"
        "- Must be based on real verifiable facts\n\n"
        "Format exactly like this:\n\n"
        "HOOK 1 [CURIOSITY GAP]: sentence here\n"
        "Virality: X/100 | Why it works: reason\n\n"
        "HOOK 2 [SHOCKING FACT]: sentence here\n"
        "Virality: X/100 | Why it works: reason\n\n"
        "HOOK 3 [COUNTERINTUITIVE]: sentence here\n"
        "Virality: X/100 | Why it works: reason\n\n"
        "HOOK 4 [IDENTITY TRIGGER]: sentence here\n"
        "Virality: X/100 | Why it works: reason\n\n"
        "HOOK 5 [STAKES/URGENCY]: sentence here\n"
        "Virality: X/100 | Why it works: reason\n\n"
        "BEST PICK: Hook N because reason"
    )

    result = ask_groq(prompt, max_tokens=800, temperature=0.9)
    if result:
        msg = "5 HOOKS FOR: " + topic.upper() + "\n"
        msg += "─────────────────────────\n"
        msg += result
        msg += "\n─────────────────────────\n"
        msg += "Use the best hook → send: 1 (or your angle number) to generate full plan"
        send(msg)
    else:
        send("Failed to generate hooks. Try again.")


# ─────────────────────────────────────────────
# NEW TOOL 2: Viral Score Predictor
# ─────────────────────────────────────────────
def handle_score(idea):
    send("Scoring viral potential of: " + idea + "...")

    prompt = (
        "You are a TikTok/YouTube algorithm expert who has analyzed 10,000+ viral videos.\n\n"
        "Rate this video idea for viral potential:\n"
        "IDEA: " + idea + "\n\n"
        "Score each factor out of 100:\n\n"
        "CURIOSITY GAP: X/100 - does it make people need to know more?\n"
        "SHAREABILITY: X/100 - will people send this to friends?\n"
        "REWATCH VALUE: X/100 - will people watch it multiple times?\n"
        "BROAD APPEAL: X/100 - can anyone relate to this?\n"
        "TREND ALIGNMENT: X/100 - is this topic currently popular?\n"
        "VISUAL POTENTIAL: X/100 - can this be made visually compelling?\n\n"
        "OVERALL VIRAL SCORE: X/100\n\n"
        "VERDICT: [SKIP IT / WORTH TRYING / HIGH POTENTIAL / VIRAL GOLDMINE]\n\n"
        "TOP 3 STRENGTHS:\n"
        "1. strength\n"
        "2. strength\n"
        "3. strength\n\n"
        "TOP 3 WEAKNESSES:\n"
        "1. weakness\n"
        "2. weakness\n"
        "3. weakness\n\n"
        "HOW TO IMPROVE IT:\n"
        "Suggest a better angle or hook to maximize viral potential"
    )

    result = ask_groq(prompt, max_tokens=700, temperature=0.7)
    if result:
        msg = "VIRAL SCORE: " + idea.upper()[:50] + "\n"
        msg += "─────────────────────────\n"
        msg += result
        msg += "\n─────────────────────────\n"
        msg += "To generate full plan for this idea: send its angle number or use hooks <topic>"
        send(msg)
    else:
        send("Failed to score idea. Try again.")


# ─────────────────────────────────────────────
# NEW TOOL 3: Series Generator
# ─────────────────────────────────────────────
def handle_series(topic):
    send("Building 5-part series for: " + topic + "...")

    prompt = (
        "You are a viral content strategist. Turn this topic into a 5-part TikTok/Shorts series.\n\n"
        "TOPIC: " + topic + "\n\n"
        "Rules:\n"
        "- Each video must stand alone AND make viewers want the next part\n"
        "- End each video with a cliffhanger that teases part N+1\n"
        "- Each video covers a different angle of the same topic\n"
        "- Series should build a loyal following over 5 videos\n\n"
        "Format:\n\n"
        "SERIES TITLE: overall series name\n"
        "SERIES HOOK: one sentence that sells the whole series\n\n"
        "PART 1: title\n"
        "Angle: what this video covers\n"
        "Hook: first sentence\n"
        "Cliffhanger: how it ends to pull viewers to part 2\n"
        "Best posting time: day and time\n\n"
        "PART 2: title\n"
        "Angle: what this video covers\n"
        "Hook: first sentence\n"
        "Cliffhanger: how it ends to pull viewers to part 3\n"
        "Best posting time: day and time\n\n"
        "PART 3: title\n"
        "Angle: what this video covers\n"
        "Hook: first sentence\n"
        "Cliffhanger: how it ends to pull viewers to part 4\n"
        "Best posting time: day and time\n\n"
        "PART 4: title\n"
        "Angle: what this video covers\n"
        "Hook: first sentence\n"
        "Cliffhanger: how it ends to pull viewers to part 5\n"
        "Best posting time: day and time\n\n"
        "PART 5: title\n"
        "Angle: what this video covers\n"
        "Hook: first sentence\n"
        "Ending: satisfying conclusion that makes them follow for more\n"
        "Best posting time: day and time\n\n"
        "GROWTH STRATEGY: how to cross-promote these 5 videos for maximum followers"
    )

    result = ask_groq(prompt, max_tokens=1200, temperature=0.85)
    if result:
        msg = "5-PART SERIES: " + topic.upper()[:50] + "\n"
        msg += "─────────────────────────\n"
        msg += result
        msg += "\n─────────────────────────\n"
        msg += "To generate full script for any part:\n"
        msg += "Send: hooks <part title> then generate from there"
        send(msg)
    else:
        send("Failed to generate series. Try again.")


# ─────────────────────────────────────────────
# NEW TOOL 4: Comment Reply Generator
# ─────────────────────────────────────────────
def handle_replies(comments_text):
    if not comments_text or len(comments_text) < 5:
        send(
            "Paste your comments after the command like this:\n\n"
            "replies\n"
            "This is amazing!\n"
            "Where did you get this info?\n"
            "I never knew this existed\n"
            "Can you make more videos like this?"
        )
        return

    send("Generating replies for your comments...")

    prompt = (
        "You are a viral TikTok creator who is great at engaging with comments to boost the algorithm.\n\n"
        "Generate replies to these comments. Rules:\n"
        "- Keep replies SHORT (1-2 sentences max)\n"
        "- Be genuine, warm, and human - not robotic\n"
        "- Ask follow-up questions to drive more comments\n"
        "- Use occasional emojis naturally\n"
        "- For questions: answer briefly then redirect curiosity\n"
        "- For praise: be grateful but humble, tease next video\n"
        "- For skeptics: be respectful, invite them to look it up\n"
        "- Every reply should make the person want to respond again\n\n"
        "COMMENTS:\n" + comments_text + "\n\n"
        "Format:\n"
        "COMMENT: [original comment]\n"
        "REPLY: [your reply]\n"
        "WHY: [one line on why this reply boosts engagement]\n\n"
        "Then at the end:\n"
        "BEST REPLY OF THE BATCH: [the one most likely to go viral in comments]"
    )

    result = ask_groq(prompt, max_tokens=900, temperature=0.8)
    if result:
        msg = "COMMENT REPLIES\n"
        msg += "─────────────────────────\n"
        msg += result
        msg += "\n─────────────────────────\n"
        msg += "Pro tip: Reply within the first hour of posting for maximum algorithm boost."
        send(msg)
    else:
        send("Failed to generate replies. Try again.")


# ─────────────────────────────────────────────
# Generate handler
# ─────────────────────────────────────────────
def handle_generate(picks, custom_angle=None):
    global is_generating
    if is_generating:
        send("Already generating, please wait...")
        return

    try:
        with open("angle_index.json") as f:
            index_map = json.load(f)
    except Exception:
        if not last_angles:
            send("No trends loaded. Send scan first.")
            return
        index_map = {str(i+1): a for i, a in enumerate(last_angles)}

    selected = [(p, index_map[str(p)]) for p in picks if str(p) in index_map]
    if not selected:
        send("Invalid numbers. Check the trend list.")
        return

    is_generating = True
    send("Generating " + str(len(selected)) + " video plan(s)... ~10 seconds each")

    for idx, angle in selected:
        send("Working on #" + str(idx) + ": " + angle["angle"][:60] + "...")
        raw = generate_video_plan(angle, custom_angle)
        if raw:
            format_and_send_plan(angle, raw, idx)
        else:
            send("Failed to generate #" + str(idx) + ". Try again.")

    send("Done! Use redo N for a fresh angle, or hooks <topic> to test different hooks.")
    is_generating = False


def handle_redo(number):
    global is_generating
    if is_generating:
        send("Already generating, please wait...")
        return

    try:
        with open("angle_index.json") as f:
            index_map = json.load(f)
    except Exception:
        send("No trends loaded. Send scan first.")
        return

    if str(number) not in index_map:
        send("Invalid number.")
        return

    angle = index_map[str(number)]
    original_topic = angle.get("source_topic", angle["angle"])
    send("Regenerating #" + str(number) + " with a fresh creative angle...")

    rethink = ask_groq(
        "Topic: " + original_topic + "\n\nGenerate 1 more creative and viral video angle. More specific, more surprising. Reply with just the angle title, max 10 words.",
        max_tokens=50, temperature=0.95
    )

    if rethink:
        send("New angle: " + rethink)
        angle["angle"] = rethink

    is_generating = True
    raw = generate_video_plan(angle)
    if raw:
        format_and_send_plan(angle, raw, number)
    else:
        send("Failed. Try again.")
    is_generating = False
    send("Send redo " + str(number) + " again for another variation.")


# ─────────────────────────────────────────────
# Message handler
# ─────────────────────────────────────────────
def handle_thumb(number):
    """Generate thumbnail for angle N and send as photo."""
    try:
        with open("angle_index.json") as f:
            index_map = json.load(f)
    except Exception:
        send("No trends loaded. Send scan first.")
        return

    if str(number) not in index_map:
        send("Invalid number. Check the trend list.")
        return

    angle = index_map[str(number)]
    send("Generating thumbnail for #" + str(number) + ": " + angle["angle"][:50] + "...")

    try:
        from thumbnail_generator import create_thumbnail
        filepath, concept = create_thumbnail(angle, number)

        # Send the PNG via Telegram
        with open(filepath, "rb") as photo:
            requests.post(
                "https://api.telegram.org/bot" + BOT_TOKEN + "/sendPhoto",
                data={"chat_id": CHAT_ID},
                files={"photo": photo},
                timeout=30
            )

        # Send concept details
        msg = "THUMBNAIL #" + str(number) + " CONCEPT\n"
        msg += "─────────────────────────\n"
        msg += "HEADLINE: " + concept["headline"] + "\n"
        msg += "SUBTEXT: " + concept["subtext"] + "\n"
        msg += "BADGE: " + concept["badge"] + "\n"
        msg += "EMOTION: " + concept["emotion"] + "\n"
        msg += "KEY VISUAL: " + concept["key_visual"] + "\n"
        msg += "─────────────────────────\n"
        msg += "To recreate in Canva:\n"
        msg += "1. Go to canva.com/create/youtube-thumbnails\n"
        msg += "2. Use the headline and layout above\n"
        msg += "3. Match the color scheme to your niche\n"
        msg += "Send thumb " + str(number) + " again for a different concept"
        send(msg)

    except Exception as e:
        send("Thumbnail generation failed: " + str(e))


def handle_message(text):
    text = text.strip()
    text_lower = text.lower()
    print("[Message] " + text[:80])

    # Help
    if text_lower in ["help", "/help", "/start"]:
        send(
            "CONTENT BOT - ALL COMMANDS\n\n"
            "TREND ALERTS:\n"
            "  scan              - scan trends now\n"
            "  status            - bot health\n\n"
            "VIDEO PLANS:\n"
            "  top3              - generate top 3\n"
            "  all               - generate top 5\n"
            "  1 3 5             - pick by number\n"
            "  redo 2            - fresh angle for #2\n\n"
            "NEW TOOLS:\n"
            "  hooks death from laughter\n"
            "                    - 5 hooks ranked by virality\n"
            "  score snow in florida\n"
            "                    - viral score 1-100\n"
            "  series black holes\n"
            "                    - 5-part content series\n"
            "  replies           - generate comment replies\n"
            "  (paste comments after 'replies')"
        )

    elif text_lower == "scan":
        send("Starting manual scan...")
        threading.Thread(target=run_scan, daemon=True).start()

    elif text_lower == "status":
        scan_time = last_scan_time.strftime("%b %d %H:%M") if last_scan_time else "Never"
        send(
            "Bot Status\n"
            "Last scan: " + scan_time + "\n"
            "Angles loaded: " + str(len(last_angles)) + "\n"
            "Generating: " + ("Yes" if is_generating else "No") + "\n"
            "AI: Groq llama-3.1-8b-instant"
        )

    elif text_lower == "top3":
        top = sorted(last_angles, key=lambda x: x.get("virality_score",0), reverse=True)[:3]
        if not top:
            send("No trends. Send scan first.")
            return
        try:
            with open("angle_index.json") as f:
                index_map = json.load(f)
            rev = {v["angle"]: k for k, v in index_map.items()}
            picks = [int(rev[a["angle"]]) for a in top if a["angle"] in rev]
        except Exception:
            picks = [1, 2, 3]
        threading.Thread(target=handle_generate, args=(picks,), daemon=True).start()

    elif text_lower == "all":
        threading.Thread(target=handle_generate, args=(list(range(1,6)),), daemon=True).start()

    elif text_lower.startswith("redo "):
        parts = text_lower.split()
        if len(parts) == 2 and parts[1].isdigit():
            threading.Thread(target=handle_redo, args=(int(parts[1]),), daemon=True).start()
        else:
            send("Usage: redo 1")

    # New tools
    elif text_lower.startswith("hooks "):
        topic = text[6:].strip()
        if topic:
            threading.Thread(target=handle_hooks, args=(topic,), daemon=True).start()
        else:
            send("Usage: hooks death from laughter")

    elif text_lower.startswith("score "):
        idea = text[6:].strip()
        if idea:
            threading.Thread(target=handle_score, args=(idea,), daemon=True).start()
        else:
            send("Usage: score snow in florida")

    elif text_lower.startswith("series "):
        topic = text[7:].strip()
        if topic:
            threading.Thread(target=handle_series, args=(topic,), daemon=True).start()
        else:
            send("Usage: series black holes")

    elif text_lower.startswith("replies"):
        # Get everything after "replies"
        comments = text[7:].strip()
        threading.Thread(target=handle_replies, args=(comments,), daemon=True).start()

    elif text_lower.startswith("audio "):
        query = text[6:].strip()
        if query:
            threading.Thread(target=handle_audio, args=(query,), daemon=True).start()
        else:
            send("Usage: audio dark mystery\nExamples:\n  audio cinematic history\n  audio upbeat science\n  audio dark mystery")

    elif text_lower.startswith("thumb "):
        parts = text_lower.split()
        if len(parts) == 2 and parts[1].isdigit():
            threading.Thread(target=handle_thumb, args=(int(parts[1]),), daemon=True).start()
        else:
            send("Usage: thumb 1  (replace 1 with the angle number)")

    else:
        numbers = re.findall(r'\d+', text)
        if numbers:
            picks = [int(n) for n in numbers]
            threading.Thread(target=handle_generate, args=(picks,), daemon=True).start()
        else:
            send("Send help to see all commands.")


# ─────────────────────────────────────────────
# Main loop
# ─────────────────────────────────────────────
def main():
    global last_update_id, last_angles
    print("Content Bot starting...")

    try:
        with open("latest_trends.json") as f:
            data = json.load(f)
        last_angles = data.get("angles", [])
        print("Loaded " + str(len(last_angles)) + " cached angles")
    except Exception:
        pass

    send(
        "Content Bot online! All features ready.\n\n"
        "NEW COMMANDS:\n"
        "  hooks <topic>   - 5 viral hooks ranked\n"
        "  score <idea>    - viral score 1-100\n"
        "  series <topic>  - 5-part content series\n"
        "  replies         - comment reply generator\n\n"
        "Send help for full command list."
    )

    last_scan_epoch = 0

    while True:
        try:
            now = time.time()
            if now - last_scan_epoch >= SCAN_INTERVAL_HOURS * 3600:
                threading.Thread(target=run_scan, daemon=True).start()
                last_scan_epoch = now

            updates = get_updates()
            for update in updates:
                last_update_id = update["update_id"]
                msg = update.get("message", {})
                if str(msg.get("chat",{}).get("id","")) == str(CHAT_ID):
                    text = msg.get("text","")
                    if text:
                        handle_message(text)

            time.sleep(2)

        except KeyboardInterrupt:
            print("Bot stopped.")
            break
        except Exception as e:
            print("[Error] " + str(e))
            time.sleep(10)


if __name__ == "__main__":
    main()


# ─────────────────────────────────────────────
# FEATURE: Trending Audio Finder
# Command: audio <mood> <niche>
# ─────────────────────────────────────────────
def handle_audio(query):
    send("Finding trending audio for: " + query + "...")

    # Scrape free music sources
    headers = {"User-Agent": "Mozilla/5.0 (compatible; ContentBot/1.0)"}
    found_tracks = []

    # 1. YouTube Audio Library RSS/search simulation via web
    # 2. Free Music Archive
    try:
        r = requests.get(
            "https://freemusicarchive.org/api/get/tracks.json?sort=track_date_recorded&d=1&limit=20",
            headers=headers, timeout=10
        )
        if r.status_code == 200:
            data = r.json()
            for track in data.get("dataset", [])[:10]:
                title = track.get("track_title", "")
                artist = track.get("artist_name", "")
                genre = track.get("track_genres", [{}])
                genre_name = genre[0].get("genre_title", "") if genre else ""
                url = track.get("track_url", "")
                if title and artist:
                    found_tracks.append({
                        "title": title,
                        "artist": artist,
                        "genre": genre_name,
                        "url": url,
                        "source": "Free Music Archive"
                    })
    except Exception as e:
        print("[FMA] " + str(e))

    # Use Groq to curate and add TikTok-specific recommendations
    prompt = (
        "You are a viral TikTok/YouTube Shorts sound expert. "
        "Recommend the best audio tracks for this video style: " + query + "\n\n"
        "Give 8 specific audio recommendations across these categories:\n\n"
        "TIKTOK TRENDING SOUNDS (3 tracks):\n"
        "For each: Track name | Artist | Why it works for this style | Where to find it\n\n"
        "YOUTUBE AUDIO LIBRARY - FREE (3 tracks):\n"
        "For each: Track name | Artist | Mood/tempo | Search term to find it at studio.youtube.com/channel/music\n\n"
        "ALTERNATIVE FREE SOURCES (2 tracks):\n"
        "For each: Track name | Artist | Source website | Why it fits\n\n"
        "PRO TIPS FOR THIS STYLE:\n"
        "- Best volume level for background music\n"
        "- When to use sound effects vs music only\n"
        "- Specific timing tricks for " + query + " style videos\n\n"
        "TIKTOK SOUND STRATEGY:\n"
        "- Should you use trending sounds or original audio for this style?\n"
        "- How to find currently trending sounds in this niche on TikTok"
    )

    result = ask_groq(prompt, max_tokens=1000, temperature=0.7)

    msg = "TRENDING AUDIO FOR: " + query.upper() + "\n"
    msg += "─────────────────────────\n"

    if found_tracks:
        msg += "LIVE TRACKS FROM FREE MUSIC ARCHIVE:\n"
        for t in found_tracks[:3]:
            msg += "  - " + t["title"] + " by " + t["artist"]
            if t["genre"]:
                msg += " [" + t["genre"] + "]"
            if t["url"]:
                msg += "\n    " + t["url"]
            msg += "\n"
        msg += "\n"

    if result:
        msg += result
    else:
        msg += "Could not generate recommendations. Try again."

    msg += "\n─────────────────────────\n"
    msg += "FREE MUSIC SOURCES:\n"
    msg += "  YouTube Audio Library: studio.youtube.com/channel/music\n"
    msg += "  Free Music Archive: freemusicarchive.org\n"
    msg += "  Pixabay Music: pixabay.com/music\n"
    msg += "  Mixkit: mixkit.co/free-music"

    send(msg)
