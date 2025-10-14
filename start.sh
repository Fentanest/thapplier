#!/bin/bash

# Debug: Print the environment variables to the log to verify they are set
echo "--- Verifying Environment Variables ---"
echo "TELEGRAM_BOT_TOKEN is set to: '${TELEGRAM_BOT_TOKEN}'"
echo "TELEGRAM_CHAT_ID is set to: '${TELEGRAM_CHAT_ID}'"
echo "------------------------------------"

# Start Gunicorn in the background
echo "Starting Gunicorn..."
gunicorn --workers 2 --threads 8 --worker-class gthread --bind 0.0.0.0:5001 --timeout 120 --access-logfile - --error-logfile - app:app &

# Start the Telegram bot in the foreground
echo "Starting Telegram Bot..."
python3 telegram_bot.py

# Wait for any process to exit
wait -n
  
# Exit with status of process that exited first
exit $?