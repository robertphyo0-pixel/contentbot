import re

with open('/home/ubuntu/content-bot/telegram_bot.py', 'r') as f:
    content = f.read()

new_func = '''def generate_video_plan(angle):
    api_key = os.getenv("GROQ_API_KEY", "")
    if not api_key:
        return None
    topic = angle["angle"]
    lines = [
        "You are a viral TikTok/YouTube Shorts scriptwriter.",
        "",
        "TOPIC: " + topic,
        "",
        "Write in this exact format:",
        "TITLE: [catchy title under 60 chars]",
        "HOOK: [shocking first sentence, never start with did you know]",
        "SCRIPT: [80 word narration, simple language, ends with cliffhanger]",
        "SCENE 1 (0-5s): [visual description]",
        "SCENE 2 (5-11s): [visual description]",
        "SCENE 3 (11-18s): [visual description]",
        "SCENE 4 (18-25s): [visual description]",
        "SCENE 5 (25-32s): [visual description]",
        "IMAGE 1: [cinematic AI image prompt, camera angle, lighting, style]",
        "IMAGE 2: [cinematic AI image prompt, camera angle, lighting, style]",
        "IMAGE 3: [cinematic AI image prompt, camera angle, lighting, style]",
        "IMAGE 4: [cinematic AI image prompt, camera angle, lighting, style]",
        "IMAGE 5: [cinematic AI image prompt, camera angle, lighting, style]",
        "MUSIC: [mood, tempo, genre, no lyrics]",
        "EFFECTS: [text overlays, zoom punches, sound effects]",
        "CAPTION: [opens with shocking statement, ends with question]",
        "HASHTAGS: #tag1 #tag2 #tag3 #tag4 #tag5 #tag6 #tag7 #tag8 #tag9 #tag10",
    ]
    prompt = "\\n".join(lines)
    try:
        r = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": "Bearer " + api_key, "Content-Type": "application/json"},
            json={"model": "llama3-8b-8192", "messages": [{"role": "user", "content": prompt}], "temperature": 0.8, "max_tokens": 1000},
            timeout=30
        )
        if r.status_code == 200:
            return r.json()["choices"][0]["message"]["content"].strip()
        else:
            print("[Groq] Error " + str(r.status_code) + ": " + r.text)
    except Exception as e:
        print("[Groq] " + str(e))
    return None'''

content = re.sub(r'def generate_video_plan\(angle\):.*?return None', new_func, content, flags=re.DOTALL)

with open('/home/ubuntu/content-bot/telegram_bot.py', 'w') as f:
    f.write(content)

print('Done!')
