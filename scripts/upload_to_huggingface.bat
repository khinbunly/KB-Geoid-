@echo off
title Deploy to Hugging Face Spaces
echo ==========================================================
echo       Deploy KB-Geoid Bot to Hugging Face Spaces
echo ==========================================================
echo.
echo Please copy your token from: https://huggingface.co/settings/tokens
echo.
set /p HF_TOKEN="Paste your Hugging Face Token (hf_...): "
if "%HF_TOKEN%"=="" (
    echo Error: Token cannot be empty.
    pause
    exit /b 1
)

python scripts/deploy_hf.py %HF_TOKEN%
pause
