@echo off
chcp 65001 > nul
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
echo 금융 인턴 공고 수집 중... (약 8~10분)
python -W ignore run.py
start "" "%~dp0dashboard.html"
