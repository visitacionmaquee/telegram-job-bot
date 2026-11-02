@echo off
title MakieJob Alert Bot
cd /d "%~dp0"
echo ========================================================
echo   MakieJob Telegram Bot - AI Job Hunter Assistant
echo ========================================================
echo.
echo Starting bot with virtual environment...
".venv\Scripts\python.exe" bot.py
pause
