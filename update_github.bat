@echo off
echo Starting TipJar GitHub Update Tool...
powershell -ExecutionPolicy Bypass -File "%~dp0update_github.ps1"
pause 