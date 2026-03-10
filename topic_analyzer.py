"""
topic_analyzer.py - IMPROVED
──────────────────────────────
MAX 2 angles per source topic — no more 8 duplicates from same source.
Better niche detection. Higher quality angles.
"""

import json
import re
from datetime import datetime



# Names/topics to skip - not educational content
SKIP_TOPICS = [
    # Celebrity names
    "michelle randolph", "mahmoud khalil", "neil gorsuch", "tom brady",
    "erika kirk", "neil gorsuch", "sag-aftra",
    # Financial tickers
    "dow jones", "nasdaq", "s&p 500", "futures", "oil price per barrel",
    "stock market", "crypto", "bitcoin", "forex", "oil price",
    # Sports
    "nfl", "nba", "mlb", "nhl", "super bowl", "willie colon",
    # Politics
    "trump", "biden", "congress", "senate", "republican", "democrat",
    # Weather services
    "weather.com", "storm prediction", "weather channel", "forecast",
    # Generic news junk
    "vs vietnam", "japan vs", "price of oil", "per barrel",
    # Developer/tech junk
    "jslinux", "x86_64", "linux kernel", "supports x86", "waitrose",
    "mackerel", "overfishing", "suspend", "sales due",
    # Weather junk
    "severe weather", "weather outlook", "storm center", "weather.com",
    "tornado watch", "hurricane", "flood warning",
    # More celebrity/people names to skip
    "corey feldman", "willie colon", "erika kirk",
    "nytimes wordle", "wordle", "marjorie taylor", "taylor greene",
    "wildfire season", "all your base", "charlie marr",
    "that during their", "thatcharlie", "thylane blondeau",
    "savannah bond", "show hn:", "remotely use",
    "spectacular images reveal", "images reveal unique",
]

# Also skip if topic is just a weather/news service phrase
def looks_like_news_junk(text):
    junk_phrases = ["outlook", "warning", "watch issued", "breaking:", "update:"]
    t = text.lower()
    return any(p in t for p in junk_phrases)


def is_junk_topic(text):
    t = text.lower()
    # Skip if matches known junk
    for skip in SKIP_TOPICS:
        if skip in t:
            return True
    # Skip if it looks like a person name (2 words, both capitalized, under 25 chars)
    words = text.strip().split()
    if len(words) == 2 and all(w[0].isupper() for w in words if w) and len(text) < 25:
        return True
    # Skip news junk phrases
    if looks_like_news_junk(text):
        return True
    # Skip garbled scraped text
    if re.match(r'^that[a-z]', text.lower()):
        return True
    if re.search(r'[a-z][A-Z]', text):
        return True
    if "(" in text and "pictured" in text.lower():
        return True
    return False

HOOK_TEMPLATES = [
    "The hidden {X} that nobody talks about",
    "Why {X} is not what you think it is",
    "What they never taught you about {X}",
    "The reason {X} exists will shock you",
    "{X} was designed for a completely different purpose",
    "The accidental invention of {X}",
    "Only 1% of people know how {X} actually works",
    "The engineering problem inside {X} nobody solved for centuries",
]

VIRAL_KEYWORDS = {
    "hidden": 20, "secret": 20, "nobody knows": 25, "never taught": 20,
    "shocking": 15, "bizarre": 15, "strange": 15, "weird": 12,
    "engineering": 10, "design": 8, "how does": 10, "why does": 10,
    "invented": 12, "discovered": 10, "history": 8, "ancient": 10,
    "science": 8, "psychology": 12, "brain": 10, "space": 15,
    "military": 12, "government": 10, "classified": 18, "unusual": 12,
    "accidental": 14, "unexpected": 12,
}

ANGLE_TEMPLATES = {
    "engineering": [
        "The hidden engineering secret inside {X}",
        "Why {X} is designed exactly this way",
        "The engineering problem nobody solved until {X}",
    ],
    "history": [
        "The forgotten story behind {X}",
        "How {X} changed history forever",
        "What history books never told you about {X}",
    ],
    "science": [
        "The counterintuitive science of {X}",
        "What scientists just discovered about {X}",
        "The surprising truth science found in {X}",
    ],
    "psychology": [
        "Why your brain reacts this way to {X}",
        "The psychological trick hidden inside {X}",
        "What {X} reveals about human behavior",
    ],
    "technology": [
        "How {X} actually works under the hood",
        "Why {X} was almost never invented",
        "The accidental discovery that created {X}",
    ],
    "general": [
        "The hidden truth about {X}",
        "Why {X} is not what most people think",
        "What nobody tells you about {X}",
        "The shocking reality behind {X}",
    ],
}


def detect_niche(topic_text):
    t = topic_text.lower()
    if any(w in t for w in ["engineer","machine","design","build","bridge","aircraft","mechanism","structure"]):
        return "engineering"
    if any(w in t for w in ["history","ancient","war","empire","century","discover","inventor","medieval","civilization"]):
        return "history"
    if any(w in t for w in ["science","biology","physics","chemical","cell","dna","quantum","species","organism","evolution"]):
        return "science"
    if any(w in t for w in ["brain","mind","psychology","behavior","cognitive","emotion","memory","mental","perception"]):
        return "psychology"
    if any(w in t for w in ["app","software","ai","robot","computer","tech","internet","data","algorithm","satellite"]):
        return "technology"
    return "general"


def score_virality(text):
    score = 50
    for kw, bonus in VIRAL_KEYWORDS.items():
        if kw in text.lower():
            score += bonus
    if 4 <= len(text.split()) <= 10:
        score += 10
    return min(score, 100)


def clean_topic(raw):
    """Return a short punchy noun phrase suitable for use in angle templates."""
    raw = re.sub(r'TIL that |TIL |Did you know |Apparently |The strange truth about: ', '', raw, flags=re.IGNORECASE)
    raw = re.sub(r'\[.*?\]', '', raw).strip(" .,!?")
    words = raw.split()

    # Already short and punchy - use as-is
    if len(words) <= 4:
        return raw

    # Long sentence - extract clean noun phrase (first 3-4 meaningful words)
    stop_words = {"that","which","is","are","was","were","has","have","in","on","at","to","a","an","the","of","and","or","but","during","while","when","how","why","what"}
    noun_words = []
    for w in words:
        if w.lower() in stop_words and len(noun_words) >= 2:
            break
        noun_words.append(w)
        if len(noun_words) >= 4:
            break

    result = " ".join(noun_words).strip(" .,!?")
    return result if len(result) > 5 else " ".join(words[:3])


# Global counter to rotate templates
_template_counter = 0

def is_short_topic(text):
    """True if topic is a short noun phrase suitable for template wrapping."""
    words = text.strip().split()
    # Short topics (1-5 words) work well in templates
    if len(words) <= 5:
        return True
    # Check if it looks like a headline/sentence
    sentence_words = {"is","are","was","were","has","have","that","which","from","during","while","when","found","creates","discovers","shows","reveals","may","could","would"}
    return not any(w.lower() in sentence_words for w in words)

def generate_angles(topic_text, niche):
    global _template_counter
    clean = clean_topic(topic_text)
    templates = ANGLE_TEMPLATES.get(niche, ANGLE_TEMPLATES["general"])

    if is_short_topic(topic_text):
        # Short topic: wrap in template
        idx = _template_counter % len(templates)
        _template_counter += 1
        angle1 = templates[idx].replace("{X}", clean)
    else:
        # Long headline: use as-is, just clean it up nicely
        angle1 = topic_text.strip(" .,!?")
        if len(angle1) > 80:
            words = angle1.split()
            angle1 = " ".join(words[:10]) + "..."
        _template_counter += 1

    angles = [{"angle": angle1, "source_topic": topic_text, "niche": niche, "virality_score": score_virality(angle1)}]

    # Only add second angle for short topics
    if is_short_topic(topic_text):
        hook_idx = _template_counter % len(HOOK_TEMPLATES)
        angle2 = HOOK_TEMPLATES[hook_idx].replace("{X}", clean)
        s2 = score_virality(angle2)
        if abs(s2 - angles[0]["virality_score"]) > 5:
            angles.append({"angle": angle2, "source_topic": topic_text, "niche": niche, "virality_score": s2})

    return angles


def analyze_topics(topics=None):
    if topics is None:
        try:
            with open("topics_cache.json") as f:
                topics = json.load(f)["topics"]
        except FileNotFoundError:
            print("❌ topics_cache.json not found.")
            return []

    print(f"\n🧠 Analyzing {len(topics)} topics...")
    all_angles = []

    # Filter junk topics before processing
    topics = [t for t in topics if not is_junk_topic(t.get("topic", ""))]
    print("  After junk filter: " + str(len(topics)) + " topics remain")

    for t in topics[:40]:
        text = t.get("topic", "")
        if len(text) < 10:
            continue
        all_angles.extend(generate_angles(text, detect_niche(text)))

    all_angles.sort(key=lambda x: x["virality_score"], reverse=True)

    seen = set()
    unique = []
    seen_source_topics = set()
    for a in all_angles:
        key = a["angle"][:40].lower()
        if key not in seen:
            seen.add(key)
            src_key = a.get("source_topic","")[:40].lower()
            if src_key not in seen_source_topics:
                seen_source_topics.add(src_key)
                unique.append(a)

    top = unique[:30]
    with open("angles_cache.json", "w") as f:
        json.dump({"timestamp": datetime.now().isoformat(), "angles": top}, f, indent=2)

    print(f"  ✅ {len(top)} unique angles from {len(topics)} topics")
    return top


if __name__ == "__main__":
    angles = analyze_topics()
    print("\nTop 10 video angles:")
    for i, a in enumerate(angles[:10], 1):
        print(f"  {i:2}. [{a['virality_score']}] {a['angle']}")
        print(f"       Niche: {a['niche']} | Source: {a['source_topic'][:50]}")
