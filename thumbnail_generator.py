"""
thumbnail_generator.py
──────────────────────
Generates YouTube thumbnail concepts via Groq
then builds a real PNG thumbnail using Pillow.
Command: thumb N  (where N is the angle number)
"""

import os
import json
import textwrap
import requests
from PIL import Image, ImageDraw, ImageFont
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
OUTPUT_DIR = os.path.expanduser("~/content-bot/thumbnails")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ─────────────────────────────────────────────
# Color themes per niche
# ─────────────────────────────────────────────
NICHE_THEMES = {
    "science":     {"bg": (10, 15, 40),    "accent": (0, 180, 255),   "text": (255, 255, 255), "glow": (0, 120, 200)},
    "history":     {"bg": (30, 20, 10),    "accent": (200, 150, 50),  "text": (255, 240, 200), "glow": (150, 100, 30)},
    "technology":  {"bg": (5, 20, 15),     "accent": (0, 255, 150),   "text": (255, 255, 255), "glow": (0, 180, 100)},
    "psychology":  {"bg": (25, 10, 35),    "accent": (180, 0, 255),   "text": (255, 255, 255), "glow": (130, 0, 200)},
    "engineering": {"bg": (20, 25, 30),    "accent": (255, 150, 0),   "text": (255, 255, 255), "glow": (200, 100, 0)},
    "general":     {"bg": (15, 15, 15),    "accent": (255, 50, 50),   "text": (255, 255, 255), "glow": (200, 0, 0)},
}

# ─────────────────────────────────────────────
# Ask Groq for thumbnail concept
# ─────────────────────────────────────────────
def get_thumbnail_concept(angle):
    topic = angle.get("angle", "")
    niche = angle.get("niche", "general")

    prompt = (
        "You are a YouTube thumbnail expert. Create a thumbnail concept for this video:\n"
        "TOPIC: " + topic + "\n"
        "NICHE: " + niche + "\n\n"
        "Respond in this exact format:\n\n"
        "HEADLINE: 2-4 words MAX, all caps, no punctuation, no markdown (example: NUCLEAR SECRET or HIDDEN TRUTH)\n"
        "SUBTEXT: 2-4 word supporting text (smaller text below headline)\n"
        "EMOTION: one word (SHOCKED/AMAZED/CURIOUS/SCARED/MIND_BLOWN)\n"
        "LAYOUT: LEFT_TEXT or RIGHT_TEXT or CENTER_TEXT\n"
        "KEY_VISUAL: describe the main image/visual element in 10 words\n"
        "BADGE_TEXT: 2-3 word badge label like SHOCKING TRUTH or NEVER SEEN"
    )

    try:
        r = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": "Bearer " + GROQ_API_KEY, "Content-Type": "application/json"},
            json={
                "model": "llama-3.1-8b-instant",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.8,
                "max_tokens": 200
            },
            timeout=20
        )
        if r.status_code == 200:
            return r.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print("[Groq thumb] " + str(e))
    return None


# ─────────────────────────────────────────────
# Parse Groq concept response
# ─────────────────────────────────────────────
def parse_concept(text):
    concept = {
        "headline": "SHOCKING TRUTH",
        "subtext": "You Won't Believe This",
        "emotion": "SHOCKED",
        "layout": "LEFT_TEXT",
        "key_visual": "dramatic close-up face with shocked expression",
        "badge": "MUST WATCH"
    }
    for line in text.split("\n"):
        line = line.strip()
        if line.startswith("HEADLINE:"):
            concept["headline"] = line[9:].strip().upper()
        elif line.startswith("SUBTEXT:"):
            concept["subtext"] = line[8:].strip()
        elif line.startswith("EMOTION:"):
            concept["emotion"] = line[8:].strip()
        elif line.startswith("LAYOUT:"):
            concept["layout"] = line[7:].strip()
        elif line.startswith("KEY_VISUAL:"):
            concept["key_visual"] = line[11:].strip()
        elif line.startswith("BADGE_TEXT:"):
            concept["badge"] = line[11:].strip().upper()
    return concept


# ─────────────────────────────────────────────
# Draw gradient background
# ─────────────────────────────────────────────
def draw_gradient(draw, width, height, color1, color2):
    for y in range(height):
        ratio = y / height
        r = int(color1[0] + (color2[0] - color1[0]) * ratio)
        g = int(color1[1] + (color2[1] - color1[1]) * ratio)
        b = int(color1[2] + (color2[2] - color1[2]) * ratio)
        draw.line([(0, y), (width, y)], fill=(r, g, b))


# ─────────────────────────────────────────────
# Draw glowing accent bar
# ─────────────────────────────────────────────
def draw_accent_bar(draw, x, y, w, h, color, glow_color):
    # Glow layers
    for i in range(8, 0, -2):
        alpha_color = tuple(min(255, int(c * 0.3)) for c in glow_color)
        draw.rectangle([x - i, y - i, x + w + i, y + h + i], fill=alpha_color)
    draw.rectangle([x, y, x + w, y + h], fill=color)


# ─────────────────────────────────────────────
# Fit text to width
# ─────────────────────────────────────────────
def fit_text(draw, text, font, max_width):
    words = text.split()
    lines = []
    current = ""
    for word in words:
        test = (current + " " + word).strip()
        bbox = draw.textbbox((0, 0), test, font=font)
        if bbox[2] - bbox[0] <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


# ─────────────────────────────────────────────
# Generate thumbnail PNG
# ─────────────────────────────────────────────
def generate_thumbnail(angle, index):
    niche = angle.get("niche", "general")
    theme = NICHE_THEMES.get(niche, NICHE_THEMES["general"])

    # Get AI concept
    raw_concept = get_thumbnail_concept(angle)
    concept = parse_concept(raw_concept) if raw_concept else parse_concept("")

    # Strip ALL markdown immediately after parsing
    concept["headline"] = concept["headline"].replace("**","").replace("*","").strip()
    concept["subtext"] = concept["subtext"].replace("**","").replace("*","").strip()
    concept["badge"] = concept["badge"].replace("**","").replace("*","").strip()[:25]

    # Canvas - YouTube thumbnail size
    W, H = 1280, 720
    img = Image.new("RGB", (W, H), theme["bg"])
    draw = ImageDraw.Draw(img)

    # Gradient background
    bg2 = tuple(min(255, c + 30) for c in theme["bg"])
    draw_gradient(draw, W, H, theme["bg"], bg2)

    # Side accent bar
    bar_w = 12
    draw_accent_bar(draw, 0, 0, bar_w, H, theme["accent"], theme["glow"])

    # Right side darker overlay for text area
    overlay_x = W // 2 if "LEFT" not in concept["layout"] else 0
    for x in range(overlay_x, W):
        alpha = 0.6
        for y in range(H):
            pass  # skip per-pixel for performance

    # Large background text (watermark style)
    try:
        big_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 160)
        med_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 80)
        small_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 42)
        badge_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 32)
        tiny_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 26)
    except Exception:
        big_font = ImageFont.load_default()
        med_font = big_font
        small_font = big_font
        badge_font = big_font
        tiny_font = big_font

    # Ghost watermark number
    ghost_color = tuple(min(255, c + 20) for c in theme["bg"])
    draw.text((W - 200, H - 220), str(index), font=big_font, fill=ghost_color)

    # Niche label top left
    niche_label = niche.upper()
    draw.rectangle([20, 20, 20 + len(niche_label) * 18 + 20, 62], fill=theme["accent"])
    draw.text((30, 24), niche_label, font=badge_font, fill=(0, 0, 0))

    # Badge top right
    badge_text = concept["badge"][:18]
    badge_w = min(len(badge_text) * 14 + 20, 380)
    draw.rectangle([W - badge_w - 20, 20, W - 20, 62], fill=(255, 200, 0))
    # Dynamically shrink badge font until text fits
    b_font = badge_font
    for font_size in [30, 26, 22, 18]:
        try:
            b_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
            test_w = draw.textbbox((0,0), badge_text, font=b_font)[2]
            if test_w <= badge_w - 16:
                break
        except Exception:
            break
    badge_pad = (42 - draw.textbbox((0,0), badge_text, font=b_font)[3]) // 2
    draw.text((W - badge_w - 8, badge_pad + 20), badge_text, font=b_font, fill=(0, 0, 0))

    # Main headline
    text_x = 40
    text_max_w = W - 80

    # Constrain text to left half only (right half is for image)
    text_max_w = (W // 2) - 60
    headline_lines = fit_text(draw, concept["headline"], med_font, text_max_w)
    headline_y = H // 2 - (len(headline_lines) * 92) // 2

    for i, line in enumerate(headline_lines[:3]):
        y = headline_y + i * 92
        # Shadow
        draw.text((text_x + 4, y + 4), line, font=med_font, fill=(0, 0, 0))
        # Main text
        draw.text((text_x, y), line, font=med_font, fill=theme["text"])
        # Accent underline on last line
        if i == len(headline_lines) - 1:
            bbox = draw.textbbox((text_x, y), line, font=med_font)
            draw.rectangle([text_x, bbox[3] + 6, bbox[2], bbox[3] + 12], fill=theme["accent"])

    # Subtext
    subtext_y = headline_y + len(headline_lines) * 92 + 20
    draw.text((text_x + 2, subtext_y + 2), concept["subtext"], font=small_font, fill=(0, 0, 0))
    draw.text((text_x, subtext_y), concept["subtext"], font=small_font, fill=theme["accent"])

    # Right side image placeholder box
    box_x = W - 420
    box_y = 80
    box_w = 380
    box_h = H - 160
    # Dark box with accent border
    draw.rectangle([box_x, box_y, box_x + box_w, box_y + box_h],
                   fill=tuple(min(255, c + 15) for c in theme["bg"]))
    draw.rectangle([box_x, box_y, box_x + box_w, box_y + 4], fill=theme["accent"])
    draw.rectangle([box_x, box_y, box_x + 4, box_y + box_h], fill=theme["accent"])
    draw.rectangle([box_x + box_w - 4, box_y, box_x + box_w, box_y + box_h], fill=theme["accent"])
    draw.rectangle([box_x, box_y + box_h - 4, box_x + box_w, box_y + box_h], fill=theme["accent"])
    # Placeholder text
    draw.text((box_x + 30, box_y + box_h//2 - 40), "ADD YOUR", font=small_font, fill=theme["glow"])
    draw.text((box_x + 30, box_y + box_h//2 + 10), "IMAGE HERE", font=small_font, fill=theme["glow"])
    draw.text((box_x + 20, box_y + box_h//2 + 60), concept["key_visual"][:25], font=tiny_font, fill=theme["accent"])

    # Bottom bar with key visual hint
    draw.rectangle([0, H - 60, W, H], fill=theme["glow"])
    visual_hint = "VISUAL: " + concept["key_visual"][:80]
    draw.text((20, H - 42), visual_hint, font=tiny_font, fill=theme["text"])

    # Save
    filename = "thumb_" + str(index) + "_" + niche + ".png"
    filepath = os.path.join(OUTPUT_DIR, filename)
    img.save(filepath, "PNG", quality=95)

    return filepath, concept


# ─────────────────────────────────────────────
# Main entry point
# ─────────────────────────────────────────────
def create_thumbnail(angle, index):
    filepath, concept = generate_thumbnail(angle, index)
    return filepath, concept


if __name__ == "__main__":
    # Test
    test_angle = {
        "angle": "Hidden metabolism found operating inside the cell nucleus",
        "niche": "science",
        "virality_score": 88
    }
    path, concept = create_thumbnail(test_angle, 5)
    print("Saved to:", path)
    print("Concept:", concept)
