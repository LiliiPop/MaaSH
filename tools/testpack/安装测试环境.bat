@echo off
rem Install a private Python + MaaFramework for the test pack (runs setup.ps1)
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup.ps1"
pause
