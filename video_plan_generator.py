"""
video_plan_generator.py
───────────────────────
Generates full production-ready video plans using local Ollama AI.
Each plan includes: hook, script, scenes, image prompts, captions, hashtags.
Engineered for TikTok/YouTube Shorts algorithm optimization.
"""

import json
import requests
import os
import time
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "mistral")
VIDEOS_PER_WEEK = int(os.getenv("VIDEOS_PER_WEEK", "3"))


# ─────────────────────────────────────────────
# Ollama API call
# ─────────────────────────────────────────────
def call_ollama(prompt, max_retries=3):
    """Send prompt to local Ollama and return text response."""
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.85,
            "top_p": 0.9,
            "num_predict": 1200,
        }
    }

    for attempt in range(max_retries):
        try:
            r = requests.post(
                f"{OLLAMA_URL}/api/generate",
                json=payload,
                timeout=600
            )
            if r.status_code == 200:
                return r.json().get("response", "").strip()
            else:
                print(f"  [Ollama] Error {r.status_code}, retrying...")
        except requests.exceptions.ConnectionError:
            print(f"  [Ollama] Not running. Start with: ollama serve")
            return None
        except Exception as e:
            print(f"  [Ollama] Attempt {attempt+1} failed: {e}")
            time.sleep(3)

    return None


# ─────────────────────────────────────────────
# Master prompt template — engineered for virality
# ─────────────────────────────────────────────
def build_video_prompt(angle_data):
    angle = angle_data["angle"]
    niche = angle_data.get("niche", "general")
    source = angle_data.get("source_topic", "")

    prompt = f"""You are an expert viral short-video scriptwriter for TikTok and YouTube Shorts.
Your videos regularly get millions of views. You understand the algorithm deeply.

Create a COMPLETE video production plan for this topic:
TOPIC: {angle}
NICHE: {niche}
SOURCE CONTEXT: {source}

STRICT REQUIREMENTS:
- Video length: 25-35 seconds (short = more rewatches = algorithm boost)
- Hook must be in the FIRST 3 WORDS — make people stop scrolling immediately
- Script uses simple language (8th grade reading level, no jargon)
- Each scene is 4-6 seconds
- End with a curiosity cliffhanger or mind-blowing conclusion
- Caption optimized for click-through (not clickbait, genuine curiosity)

OUTPUT FORMAT (use these exact headers):

TITLE: [punchy title under 60 chars]

HOOK (first 3 seconds): [the exact first sentence — must start mid-action or with a shocking fact]

VOICE STYLE: [e.g. "calm documentary narrator" / "excited discovery" / "whisper mystery"]

NARRATION SCRIPT:
[Full word-for-word script. 70-90 words max. Include natural pauses with ...]

SCENE BREAKDOWN:
Scene 1 (0-5s): [visual description]
Scene 2 (5-11s): [visual description]
Scene 3 (11-18s): [visual description]
Scene 4 (18-25s): [visual description]
Scene 5 (25-32s): [visual description]

IMAGE PROMPTS:
Prompt 1: [cinematic, detailed AI image generation prompt for Scene 1]
Prompt 2: [cinematic, detailed AI image generation prompt for Scene 2]
Prompt 3: [cinematic, detailed AI image generation prompt for Scene 3]
Prompt 4: [cinematic, detailed AI image generation prompt for Scene 4]
Prompt 5: [cinematic, detailed AI image generation prompt for Scene 5]

EDITING INSTRUCTIONS:
[Specific: cuts, text overlays, sound effects, pacing notes]

CAPTION (TikTok/YouTube):
[2-3 sentences. Opens with a question or shocking statement. Max 150 chars first line for preview.]

HASHTAGS:
[12 hashtags: mix of niche, trending, broad — no spaces in tags]

THUMBNAIL CONCEPT:
[Description of the thumbnail image + text overlay for YouTube]

Now write the complete plan:"""

    return prompt


# ─────────────────────────────────────────────
# Parse Ollama output into structured dict
# ─────────────────────────────────────────────
def parse_video_plan(raw_text, angle_data):
    """Extract sections from Ollama's response into structured data."""
    plan = {
        "angle": angle_data["angle"],
        "niche": angle_data.get("niche", "general"),
        "virality_score": angle_data.get("virality_score", 0),
        "generated_at": datetime.now().isoformat(),
        "raw": raw_text,
        "title": "",
        "hook": "",
        "voice_style": "",
        "script": "",
        "scenes": [],
        "image_prompts": [],
        "editing": "",
        "caption": "",
        "hashtags": [],
        "thumbnail": ""
    }

    if not raw_text:
        return plan

    lines = raw_text.split("\n")
    current_section = None
    buffer = []

    section_map = {
        "TITLE:": "title",
        "HOOK": "hook",
        "VOICE STYLE:": "voice_style",
        "NARRATION SCRIPT:": "script",
        "SCENE BREAKDOWN:": "scenes",
        "IMAGE PROMPTS:": "image_prompts",
        "EDITING INSTRUCTIONS:": "editing",
        "CAPTION": "caption",
        "HASHTAGS:": "hashtags",
        "THUMBNAIL CONCEPT:": "thumbnail"
    }

    def flush(section, buf):
        text = "\n".join(buf).strip()
        if not text or not section:
            return

        if section == "title":
            plan["title"] = text.replace("TITLE:", "").strip()
        elif section == "hook":
            plan["hook"] = text
        elif section == "voice_style":
            plan["voice_style"] = text
        elif section == "script":
            plan["script"] = text
        elif section == "scenes":
            for line in buf:
                if line.strip().startswith("Scene"):
                    plan["scenes"].append(line.strip())
        elif section == "image_prompts":
            for line in buf:
                if line.strip().startswith("Prompt"):
                    p = line.split(":", 1)[-1].strip()
                    if p:
                        plan["image_prompts"].append(p)
        elif section == "editing":
            plan["editing"] = text
        elif section == "caption":
            plan["caption"] = text
        elif section == "hashtags":
            # Extract hashtags
            all_text = " ".join(buf)
            tags = [t.strip() for t in all_text.split() if t.strip().startswith("#")]
            plan["hashtags"] = tags[:15]
        elif section == "thumbnail":
            plan["thumbnail"] = text

    for line in lines:
        matched = False
        for marker, section_key in section_map.items():
            if marker in line.upper():
                flush(current_section, buffer)
                current_section = section_key
                buffer = [line.split(":", 1)[-1].strip() if ":" in line else ""]
                matched = True
                break
        if not matched and current_section:
            buffer.append(line)

    flush(current_section, buffer)
    return plan


# ─────────────────────────────────────────────
# Generate all video plans for the week
# ─────────────────────────────────────────────
def generate_weekly_plans(angles=None):
    """Generate N video plans from top angles."""

    if angles is None:
        try:
            with open("angles_cache.json") as f:
                data = json.load(f)
            angles = data["angles"]
        except FileNotFoundError:
            print("❌ angles_cache.json not found. Run topic_analyzer.py first.")
            return []

    # Pick top N angles by virality score
    top_angles = sorted(angles, key=lambda x: x["virality_score"], reverse=True)[:VIDEOS_PER_WEEK]

    print(f"\n🎬 Generating {VIDEOS_PER_WEEK} video plans with Ollama ({OLLAMA_MODEL})...")
    print(f"  This takes 2-5 minutes per video...\n")

    plans = []

    for i, angle in enumerate(top_angles, 1):
        print(f"  [{i}/{VIDEOS_PER_WEEK}] Generating: {angle['angle'][:60]}...")

        prompt = build_video_prompt(angle)
        raw = call_ollama(prompt)

        if raw:
            plan = parse_video_plan(raw, angle)
            plans.append(plan)
            print(f"    ✅ Done — Title: {plan.get('title', 'N/A')[:50]}")
        else:
            print(f"    ❌ Failed to generate plan for this angle")

        # Small delay between generations
        if i < len(top_angles):
            time.sleep(2)

    # Save plans
    output = {
        "week": datetime.now().strftime("%Y-W%W"),
        "generated_at": datetime.now().isoformat(),
        "plans": plans
    }

    with open("weekly_plans.json", "w") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"\n  ✅ {len(plans)} video plans saved to weekly_plans.json")
    return plans


if __name__ == "__main__":
    plans = generate_weekly_plans()
    if plans:
        print(f"\n📋 Preview of Video 1:")
        p = plans[0]
        print(f"  Title:  {p.get('title')}")
        print(f"  Hook:   {p.get('hook')}")
        print(f"  Script: {p.get('script', '')[:200]}...")
