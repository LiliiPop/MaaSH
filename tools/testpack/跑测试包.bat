@echo off
rem Run a test suite. Default: suites\<standard>.json. Drag another suite file onto this bat to run it.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0run.ps1" -Suite "%~1"
pause
