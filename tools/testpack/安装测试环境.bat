@echo off
chcp 65001 >nul
setlocal
rem 给测试包装一个独立的 Python（放在本文件夹的 python\ 里，不影响电脑上其他东西），只需要运行一次
cd /d "%~dp0"
set "PYV=3.12.7"
if exist "python\python.exe" (
  echo 已经装过了：python\python.exe
  goto :pip
)
echo [1/3] 下载 Python %PYV% 便携版……
powershell -NoProfile -Command "$ProgressPreference='SilentlyContinue'; Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/%PYV%/python-%PYV%-embed-amd64.zip' -OutFile 'python.zip'" || (echo 下载失败，请检查网络 & pause & exit /b 1)
powershell -NoProfile -Command "Expand-Archive -Force 'python.zip' 'python'" || (echo 解压失败 & pause & exit /b 1)
del python.zip
rem 便携版默认不加载 site-packages，打开它
powershell -NoProfile -Command "(Get-Content 'python\python312._pth') -replace '^#import site','import site' | Set-Content 'python\python312._pth'"
echo [2/3] 安装 pip……
powershell -NoProfile -Command "$ProgressPreference='SilentlyContinue'; Invoke-WebRequest -Uri 'https://bootstrap.pypa.io/get-pip.py' -OutFile 'get-pip.py'" || (echo 下载 pip 失败 & pause & exit /b 1)
python\python.exe get-pip.py --no-warn-script-location || (echo 安装 pip 失败 & pause & exit /b 1)
del get-pip.py
:pip
echo [3/3] 安装 MaaFramework（和 MaaSH 用的同一个版本）……
python\python.exe -m pip install --no-warn-script-location -U "maafw==5.14.3" pillow || (echo 安装失败 & pause & exit /b 1)
if not exist accounts.json copy accounts.example.json accounts.json >nul
echo.
echo 装好了。下一步：用记事本打开 accounts.json，把「账号1」「账号2」改成网易登录框历史账号列表里显示的文字，然后双击 跑测试包.bat
pause
