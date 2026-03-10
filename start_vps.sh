#!/bin/bash
# ============================================================
# start_vps.sh — Start the VPS scanner as background service
# Run once: bash start_vps.sh
# ============================================================

cd ~/content-bot
source venv/bin/activate

# Kill any existing scanner
pkill -f vps_scanner.py 2>/dev/null

# Start scanner in background
nohup python3 vps_scanner.py > logs/scanner.log 2>&1 &
PID=$!

echo ""
echo "✅ VPS Scanner started (PID: $PID)"
echo "   Scans every 6 hours"
echo "   Alerts sent to your Telegram"
echo ""
echo "📋 Useful commands:"
echo "   View logs:    tail -f ~/content-bot/logs/scanner.log"
echo "   Stop scanner: pkill -f vps_scanner.py"
echo "   Check status: pgrep -f vps_scanner.py && echo running || echo stopped"
echo ""
