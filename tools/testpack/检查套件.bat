@echo off
rem Check a suite file without touching the emulator.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0run.ps1" -Suite "%~1" -Check
pause
