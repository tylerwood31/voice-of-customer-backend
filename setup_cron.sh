#!/bin/bash
# Setup cron job for weekly response times cache updates on Sundays at 11:59 PM EST

SCRIPT_PATH="/Users/tylerwood/voice_of_customer/backend/update_response_times_cache.py"
PYTHON_PATH="/usr/bin/python3"

# Create the cron job entry
# Runs every Sunday at 23:59 (11:59 PM)
CRON_ENTRY="59 23 * * 0 cd /Users/tylerwood/voice_of_customer/backend && $PYTHON_PATH $SCRIPT_PATH >> /Users/tylerwood/voice_of_customer/backend/cron.log 2>&1"

echo "Setting up cron job for weekly response times cache updates..."
echo "Schedule: Sundays at 11:59 PM EST"
echo "Command: $CRON_ENTRY"

# Add to crontab (check if already exists first)
(crontab -l 2>/dev/null | grep -v "$SCRIPT_PATH"; echo "$CRON_ENTRY") | crontab -

echo "✅ Cron job added successfully!"
echo ""
echo "To verify the cron job was added, run:"
echo "  crontab -l"
echo ""
echo "To view cron logs, check:"
echo "  tail -f /Users/tylerwood/voice_of_customer/backend/cron.log"