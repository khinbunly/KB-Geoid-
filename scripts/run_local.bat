@echo off
title KB-Geoid Telegram Bot
echo ==========================================================
echo           Starting KB-Geoid Telegram Bot (Local)
echo ==========================================================

REM Check if .env exists
if not exist .env (
    echo [WARNING] .env file not found. Copying from .env.example...
    copy .env.example .env
    echo [ACTION] Please edit .env and insert your TELEGRAM_BOT_TOKEN.
    pause
    exit /b 1
)

python app/main.py
pause
