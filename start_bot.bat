@echo off
echo ==========================================
echo   Starting Crypto Alert Bot
echo ==========================================
echo.

echo Starting bot...
python crypto_bot.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Bot stopped with errors.
)

pause
