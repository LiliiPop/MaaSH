@echo off
chcp 65001 >nul
rem 不连模拟器，只检查套件里的任务名、选项写得对不对
cd /d "%~dp0"
set "SUITE=%~1"
if "%SUITE%"=="" set "SUITE=suites\标准.json"
python\python.exe run_suite.py "%SUITE%" --check
pause
