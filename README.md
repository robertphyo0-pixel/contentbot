# 🎬 Content Bot — Viral Short Video Automation

Automatically researches trending topics, generates full TikTok/YouTube Shorts
production plans, and delivers them to your Telegram every Sunday.

---

## What It Does

Every week you receive 3 ready-to-produce video plans in Telegram, each with:
- ✅ Viral hook (engineered for scroll-stop)
- ✅ Full word-for-word script (25–35 seconds)
- ✅ Scene breakdown (5 scenes)
- ✅ 5 AI image generation prompts (copy-paste into Leonardo/Midjourney)
- ✅ Voice style instructions
- ✅ Editing notes
- ✅ Caption + 12 hashtags
- ✅ Thumbnail concept

**Your job:** Generate the images, record voice, assemble in CapCut. ~20 min per video.

---

## Quick Start (on your VPS)

```bash
# 1. Clone / copy files to your VPS
mkdir ~/content-bot && cd ~/content-bot
# (upload all .py files here)

# 2. Run setup (installs everything including Ollama + mistral AI)
bash setup.sh

# 3. Edit your config
nano .env
# Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID

# 4. Test everything works
source venv/bin/activate
python3 test_run.py

# 5. Run manually for first time
python3 scheduler.py

# 6. Set up weekly automation (Sunday 9AM)
crontab -e
# Add this line:
# 0 9 * * 0 cd ~/content-bot && source venv/bin/activate && python3 scheduler.py >> logs/cron.log 2>&1
```

---

## Getting Your Telegram Bot

1. Open Telegram → search **@BotFather**
2. Send `/newbot`
3. Give it any name (e.g. "My Content Bot")
4. Copy the **TOKEN** it gives you → paste in `.env`

**Get your Chat ID:**
```bash
# Replace YOUR_TOKEN with the token from BotFather
curl "https://api.telegram.org/botYOUR_TOKEN/getUpdates"
# Send a message to your bot first, then run this
# Look for "chat":{"id": 123456789}  ← that's your CHAT_ID
```

---

## File Structure

```
content-bot/
├── setup.sh              ← Run once to install everything
├── scheduler.py          ← Main pipeline (run this or let cron run it)
├── trend_scanner.py      ← Scans Google Trends, Reddit, Wikipedia, HN
├── topic_analyzer.py     ← Converts trends → viral video angles
├── video_plan_generator.py ← AI generates full production plans
├── telegram_sender.py    ← Formats & sends to your phone
├── test_run.py           ← Test each component before automating
├── .env                  ← Your config (tokens, settings)
├── topics_cache.json     ← Auto-generated trend data
├── angles_cache.json     ← Auto-generated video angles
├── weekly_plans.json     ← This week's video plans
└── logs/
    ├── bot.log           ← Full pipeline logs
    └── runs.json         ← Run history
```

---

## Running Individual Steps

```bash
source venv/bin/activate

# Run full pipeline
python3 scheduler.py

# Run individual steps
python3 scheduler.py scan       # Just scan trends
python3 scheduler.py analyze    # Just analyze topics
python3 scheduler.py generate   # Just generate plans
python3 scheduler.py send       # Just send to Telegram

# Test Telegram connection
python3 telegram_sender.py test

# Check last run status
python3 scheduler.py status
```

---

## Trend Sources

| Source | What it finds |
|--------|---------------|
| Google Trends | What people are actively searching |
| Reddit (10 subreddits) | Viral curiosity posts with 1000+ upvotes |
| Wikipedia "Did You Know" | Fascinating facts ready for video |
| Hacker News | Tech/science stories getting traction |

---

## AI Model

Running **Mistral** locally via Ollama — 100% free, private, no API costs.

If you want better quality (slower), switch to:
```
OLLAMA_MODEL=llama3  # in .env
ollama pull llama3   # download it
```

---

## Production Workflow (per video, ~20 min)

1. **Images** → Copy the 5 image prompts → paste into [Leonardo.ai](https://leonardo.ai) (free tier)
2. **Voice** → Paste script into CapCut AI voice (or record yourself)
3. **Edit** → Import images + audio into CapCut vertical template
4. **Export** → 1080×1920, 30fps
5. **Post** → TikTok first, then YouTube Shorts

---

## Scaling (after 30 videos)

Track which topics drive comments and shares. Update `NICHE_KEYWORDS` in `.env`
to focus on your best-performing niches. The bot will automatically prioritize those.

---

## Troubleshooting

**Ollama not running:**
```bash
ollama serve &
# or
sudo systemctl start ollama
```

**No topics found:**
```bash
python3 scheduler.py scan  # run just the scanner with verbose output
```

**Telegram not sending:**
```bash
python3 telegram_sender.py test
# Check BOT_TOKEN and CHAT_ID in .env
```

**Out of memory (Ollama):**
```bash
# Switch to smaller model
# In .env: OLLAMA_MODEL=tinyllama
ollama pull tinyllama
```
