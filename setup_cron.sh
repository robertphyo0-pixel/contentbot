#!/bin/bash
# setup_cron.sh
# Sets up all automated schedules:
#   - Daily 8AM report
#   - Keep bot alive (restart if crashed)

cd ~/content-bot
source venv/bin/activate

echo "Setting up cron jobs..."

# Write cron jobs
(crontab -l 2>/dev/null; echo "# Content Bot - Daily 8AM Report") | crontab -
(crontab -l 2>/dev/null; echo "30 1 * * * cd ~/content-bot && source venv/bin/activate && python3 daily_report.py >> logs/daily_report.log 2>&1") | crontab -

# Keep bot alive - check every 5 minutes and restart if crashed
(crontab -l 2>/dev/null; echo "# Content Bot - Keep alive check every 5 min") | crontab -
(crontab -l 2>/dev/null; echo "*/5 * * * * pgrep -f telegram_bot.py > /dev/null || (cd ~/content-bot && source venv/bin/activate && nohup python3 telegram_bot.py >> logs/bot_telegram.log 2>&1 &)") | crontab -

echo ""
echo "Cron jobs set:"
crontab -l
echo ""
echo "Daily report: every day at 8:00 AM"
echo "Bot watchdog: restarts bot if it crashes (every 5 min)"
echo ""
echo "Test daily report now:"
echo "  python3 daily_report.py"
