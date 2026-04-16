@echo off
echo Stopping old server...
taskkill /F /IM python.exe /T 2>nul
timeout /t 2 /nobreak >nul
echo Starting fresh server...
cd /d "d:\THUMBNAIL MODULE"
python -m cli.main studio
