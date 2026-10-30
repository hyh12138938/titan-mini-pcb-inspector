<#
    Titan Mini PCB Inspector —— 卸载
    删除安装目录、桌面与开始菜单快捷方式。不会动你的仓库和 SDK。
#>
[CmdletBinding()]
param(
    [string]$InstallDir = "$env:LOCALAPPDATA\TitanPcbInspector",
    [switch]$KeepConfig
)

$ErrorActionPreference = "Continue"
$AppName = "Titan Mini PCB Inspector"

Write-Host ""
Write-Host "  卸载 $AppName" -ForegroundColor Cyan
Write-Host "  目录: $InstallDir" -ForegroundColor Gray

if (-not (Test-Path $InstallDir)) {
    Write-Host "  目录不存在，无需卸载。" -ForegroundColor Yellow
    exit 0
}

$apiKey = Join-Path $InstallDir "api_key.txt"
if ((Test-Path $apiKey) -and -not $KeepConfig) {
    Write-Host "  将同时删除 api_key.txt（你的密钥只存在本地，删了就没了）" -ForegroundColor Yellow
}

# 快捷方式
$desktop = [Environment]::GetFolderPath("Desktop")
$startMenu = Join-Path ([Environment]::GetFolderPath("Programs")) $AppName
Get-ChildItem $desktop -Filter "$AppName*.lnk" -ErrorAction SilentlyContinue | Remove-Item -Force
if (Test-Path $startMenu) { Remove-Item $startMenu -Recurse -Force }

# 保留配置（可选）
if ($KeepConfig) {
    $keep = Join-Path $env:LOCALAPPDATA "TitanPcbInspector_config_backup"
    New-Item -ItemType Directory -Force -Path $keep | Out-Null
    foreach ($f in @("config.json", "api_key.txt")) {
        $p = Join-Path $InstallDir $f
        if (Test-Path $p) { Copy-Item $p $keep -Force }
    }
    Write-Host "  配置已备份到: $keep" -ForegroundColor Green
}

Remove-Item $InstallDir -Recurse -Force
Write-Host "  已删除安装目录。" -ForegroundColor Green
Write-Host "  卸载完成。" -ForegroundColor Green
Write-Host ""
