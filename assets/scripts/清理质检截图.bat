@echo off
chcp 65001 >nul
setlocal
rem 删除 MaaSH 质检截图文件夹里 N 天前的图片（默认 7 天）
rem 用法：清理质检截图.bat [天数]
rem       清理质检截图.bat [天数] auto   不提问，直接清理（给 Windows 定时任务用）
set "DIR=%~dp0debug\screencap"
set "DAYS=%~1"
if "%DAYS%"=="" set "DAYS=7"
if exist "%DIR%" goto clean
echo 还没有质检截图。
if /i not "%~2"=="auto" pause
exit /b 0
:clean
forfiles /p "%DIR%" /m *.* /d -%DAYS% /c "cmd /c del /q @path" 2>nul
echo 已删除 %DAYS% 天前的质检截图（%DIR%）。
if /i "%~2"=="auto" exit /b 0
echo.
set /p "ANS=要不要设成每天 12:00 自动清理 %DAYS% 天前的图？(y/N) "
if /i "%ANS%"=="y" (
  schtasks /create /f /sc daily /st 12:00 /tn "MaaSH 清理质检截图" /tr "\"%~f0\" %DAYS% auto" >nul && echo 已设置。不想要了可以在 Windows「任务计划程序」里删除「MaaSH 清理质检截图」。
)
pause
endlocal
