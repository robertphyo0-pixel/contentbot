#!/bin/bash
# ============================================================
# CONTENT BOT - Full Setup Script for Amazon VPS (Ubuntu)
# Run once: bash setup.sh
# ============================================================

set -e

echo ""
echo "╔══════════════════════════════════════════╗"
echo "║   CONTENT BOT - VPS SETUP                ║"
echo "╚══════════════════════════════════════════╝"
echo ""

# ── 1. System packages ──────────────────────────────────────
echo "[1/6] Installing system packages..."
sudo apt-get update -q
sudo apt-get install -y python3 python3-pip python3-venv curl cron

# ── 2. Python virtual environment ───────────────────────────
echo "[2/6] Creating Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

pip install --upgrade pip -q
pip install -q \
  pytrends \
  requests \
  beautifulsoup4 \
  praw \
  python-dotenv \
  schedule

echo "✅ Python packages installed."

# ── 3. Install Ollama ────────────────────────────────────────
echo "[3/6] Installing Ollama..."
if ! command -v ollama &> /dev/null; then
  curl -fsSL https://ollama.com/install.sh | sh
  echo "✅ Ollama installed."
else
  echo "✅ Ollama already installed, skipping."
fi

# ── 4. Start Ollama service ──────────────────────────────────
echo "[4/6] Starting Ollama service..."
sudo systemctl enable ollama 2>/dev/null || true
sudo systemctl start ollama  2>/dev/null || true
sleep 3

# ── 5. Pull AI model ─────────────────────────────────────────
echo "[5/6] Pulling AI model (mistral 4GB — this takes a few minutes)..."
ollama pull mistral
echo "✅ Model ready."

# ── 6. Create .env file if missing ──────────────────────────
echo "[6/6] Setting up .env config..."
if [ ! -f .env ]; then
cat > .env << 'EOF'
# ── Telegram ─────────────────────────────────────
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here

# ── Reddit API (free at reddit.com/prefs/apps) ───
REDDIT_CLIENT_ID=your_reddit_client_id
REDDIT_CLIENT_SECRET=your_reddit_secret
REDDIT_USER_AGENT=ContentBot/1.0

# ── AI Model ─────────────────────────────────────
OLLAMA_MODEL=mistral
OLLAMA_URL=http://localhost:11434

# ── Settings ──────────────────────────────────────
VIDEOS_PER_WEEK=3
NICHE_KEYWORDS=engineering,history,science,technology,psychology,nature,space
EOF
  echo "✅ .env created — EDIT IT with your Telegram token before running!"
else
  echo "✅ .env already exists, skipping."
fi

# ── 7. Set up weekly cron job ────────────────────────────────
echo ""
echo "To enable weekly Sunday 9AM automation, run:"
echo "  crontab -e"
echo "  Then add this line:"
echo "  0 9 * * 0 cd $(pwd) && source venv/bin/activate && python3 scheduler.py >> logs/cron.log 2>&1"
echo ""

mkdir -p logs prompts

echo ""
echo "╔══════════════════════════════════════════╗"
echo "║   SETUP COMPLETE ✅                       ║"
echo "╠══════════════════════════════════════════╣"
echo "║  Next steps:                              ║"
echo "║  1. Edit .env with your Telegram token    ║"
echo "║  2. python3 test_run.py  (test it)        ║"
echo "║  3. Add cron job for automation           ║"
echo "╚══════════════════════════════════════════╝"
