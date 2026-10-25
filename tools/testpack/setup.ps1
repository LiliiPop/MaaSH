# MaaSH 测试包：安装独立的 Python 和 MaaFramework（只装在本文件夹的 python\ 里）
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
[Console]::OutputEncoding = [Text.Encoding]::UTF8
Set-Location $PSScriptRoot
$pyv = '3.12.7'
$py = Join-Path $PSScriptRoot 'python\python.exe'
try {
    if (-not (Test-Path $py)) {
        Write-Host "[1/3] 下载 Python $pyv 便携版……"
        Invoke-WebRequest -Uri "https://www.python.org/ftp/python/$pyv/python-$pyv-embed-amd64.zip" -OutFile 'python.zip'
        Expand-Archive -Force 'python.zip' 'python'
        Remove-Item 'python.zip'
        # 便携版默认不加载 site-packages，打开它
        $pth = Get-ChildItem 'python\python*._pth' | Select-Object -First 1
        (Get-Content $pth.FullName) -replace '^#\s*import site', 'import site' | Set-Content $pth.FullName -Encoding ASCII
        Write-Host '[2/3] 安装 pip……'
        Invoke-WebRequest -Uri 'https://bootstrap.pypa.io/get-pip.py' -OutFile 'get-pip.py'
        & $py get-pip.py --no-warn-script-location
        if ($LASTEXITCODE -ne 0) { throw '安装 pip 失败' }
        Remove-Item 'get-pip.py'
    } else {
        Write-Host '已经装过 Python，只更新 MaaFramework'
    }
    Write-Host '[3/3] 安装 MaaFramework（和 MaaSH 同一个版本）……'
    & $py -m pip install --no-warn-script-location -U 'maafw==5.14.3' pillow
    if ($LASTEXITCODE -ne 0) { throw '安装 MaaFramework 失败' }
    if (-not (Test-Path 'accounts.json')) { Copy-Item 'accounts.example.json' 'accounts.json' }
    Write-Host ''
    Write-Host '装好了。下一步：用记事本打开 accounts.json，把「账号1」「账号2」改成网易登录框历史账号列表里显示的文字，然后运行 跑测试包.bat' -ForegroundColor Green
} catch {
    Write-Host ''
    Write-Host "出错了：$($_.Exception.Message)" -ForegroundColor Red
    Write-Host '多半是网络问题（python.org / pypi.org 连不上）。可以换个网络或开代理后再运行一次。'
}
