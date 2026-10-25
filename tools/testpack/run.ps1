# MaaSH 测试包：运行套件
param([string]$Suite = '', [switch]$Check, [string]$Only = '')
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'
Set-Location $PSScriptRoot
$py = Join-Path $PSScriptRoot 'python\python.exe'
if (-not (Test-Path $py)) { Write-Host '还没装测试环境：先运行「安装测试环境.bat」' -ForegroundColor Red; exit 1 }
if (-not $Suite) { $Suite = Join-Path $PSScriptRoot 'suites\标准.json' }
$argsList = @('run_suite.py', $Suite)
if ($Check) { $argsList += '--check' }
else {
    if (Get-Process -Name 'MFAAvalonia', 'MaaSH' -ErrorAction SilentlyContinue) {
        Write-Host '请先关掉 MaaSH（两边同时控制模拟器会互相抢）' -ForegroundColor Red; exit 1
    }
}
if ($Only) { $argsList += @('--only', $Only) }
& $py @argsList
if (-not $Check) { Write-Host ''; Write-Host '报告在 F:\MaaSH\testreports 里最新的文件夹（报告.md）。' }
