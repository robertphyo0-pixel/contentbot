#!/bin/bash
# start_bot.sh — Start the two-way Telegram bot
# Run once: bash start_bot.sh

cd ~/content-bot
source venv/bin/activate

# Stop old scanner if running
pkill -f vps_scanner.py 2>/dev/null
pkill -f telegram_bot.py 2>/dev/null
sleep 1

# Start new two-way bot
nohup python3 telegram_bot.py > logs/bot_telegram.log 2>&1 &
PID=$!

echo ""
echo "✅ Telegram Bot started (PID: $PID)"
echo ""
echo "📋 Commands to send from Telegram:"
echo "   scan    → trigger scan now"
echo "   top3    → generate top 3 videos"
echo "   1 3 5   → generate specific angles"
echo "   status  → check bot health"
echo ""
echo "📋 VPS commands:"
echo "   View logs:  tail -f ~/content-bot/logs/bot_telegram.log"
echo "   Stop bot:   pkill -f telegram_bot.py"
echo "   Restart:    bash start_bot.sh"
echo ""
