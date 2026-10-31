@echo off
cd /d "%~dp0fincoach"
call npm install
call npm run dev
