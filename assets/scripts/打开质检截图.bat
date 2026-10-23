@echo off
chcp 65001 >nul
rem 打开 MaaSH 的质检截图文件夹（任务选项「质检截图」开启后，任务完成时的截图存在这里）
if not exist "%~dp0debug\screencap" mkdir "%~dp0debug\screencap"
start "" explorer "%~dp0debug\screencap"
