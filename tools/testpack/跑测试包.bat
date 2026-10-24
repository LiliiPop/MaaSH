@echo off
chcp 65001 >nul
setlocal
rem 跑测试包：默认跑 suites\标准.json；要跑别的就把套件文件拖到这个 bat 上，或：跑测试包.bat suites\快速.json
cd /d "%~dp0"
if not exist "python\python.exe" (echo 还没装测试环境：先双击「安装测试环境.bat」 & pause & exit /b 1)
tasklist /fi "imagename eq MFAAvalonia.exe" 2>nul | find /i "MFAAvalonia.exe" >nul && (echo 请先关掉 MaaSH（两边同时控制模拟器会互相抢）& pause & exit /b 1)
set "SUITE=%~1"
if "%SUITE%"=="" set "SUITE=suites\标准.json"
python\python.exe run_suite.py "%SUITE%" %2 %3 %4
echo.
echo 报告在 F:\MaaSH\testreports 里最新的文件夹（报告.md）。
pause
