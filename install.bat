@echo off
echo ==========================================
echo   Installing Crypto Alert Bot
echo ==========================================
echo.

echo Installing Python dependencies...
pip install -r requirements.txt

echo.
echo ==========================================
echo Installation complete!
echo ==========================================
echo.
echo Next steps:
echo 1. Get your bot token from @BotFather on Telegram
echo 2. Run: SET TELEGRAM_BOT_TOKEN=your_token_here
echo 3. Run: python crypto_bot.py
echo.
pause
