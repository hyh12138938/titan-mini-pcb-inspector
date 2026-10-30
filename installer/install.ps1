<#
    Titan Mini PCB Inspector —— PC 侧一键安装脚本
    用法：右键「以 PowerShell 运行」，或双击 install.cmd
#>
[CmdletBinding()]
param(
    [string]$InstallDir = "$env:LOCALAPPDATA\TitanPcbInspector",
    [switch]$Silent,                        # 静默（不提问，用于自动化）
    [string]$ApiKey = "",
    [string]$SerialPort = "auto",
    [switch]$SkipPythonPackages
)

$ErrorActionPreference = "Stop"
$AppName     = "Titan Mini PCB Inspector"
$PayloadDir  = Join-Path $PSScriptRoot "payload"
$Marker      = Join-Path $InstallDir ".installed"

function Say($msg, $color = "Gray") { Write-Host $msg -ForegroundColor $color }
function Step($n, $msg) { Write-Host ""; Write-Host "[$n] $msg" -ForegroundColor Cyan }

function Find-Python {
    foreach ($cand in @("python", "py")) {
        $cmd = Get-Command $cand -ErrorAction SilentlyContinue
        if ($cmd) {
            $v = & $cmd.Source -c "import sys;print('%d.%d' % sys.version_info[:2])" 2>$null
            if ($v -and [version]$v -ge [version]"3.9") { return $cmd.Source }
        }
    }
    return $null
}

Write-Host ""
Write-Host "  $AppName — installer" -ForegroundColor White
Write-Host "  --------------------------------------------" -ForegroundColor DarkGray
Say "  安装目录: $InstallDir"

# ---------- 1. Python ----------
Step 1 "检查 Python"
$py = Find-Python
if (-not $py) {
    Say "  未找到 Python 3.9+。" "Yellow"
    Say "  请先安装: https://www.python.org/downloads/  (安装时勾选 Add python.exe to PATH)" "Yellow"
    Say "  或执行:   winget install -e --id Python.Python.3.12" "Yellow"
    if (-not $Silent) { Read-Host "  装好后按回车重试（Ctrl+C 退出）" | Out-Null; $py = Find-Python }
    if (-not $py) { throw "Python 缺失，安装中止。" }
}
Say "  使用: $py"

# ---------- 2. 目录 ----------
Step 2 "创建安装目录并复制文件"
if (-not (Test-Path $PayloadDir)) { throw "安装包不完整：找不到 payload 目录（$PayloadDir）" }
New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null
Copy-Item (Join-Path $PayloadDir "*") $InstallDir -Recurse -Force
Say "  已复制 $((Get-ChildItem $PayloadDir -Recurse -File).Count) 个文件"

# ---------- 3. 依赖 ----------
Step 3 "安装 Python 依赖"
if ($SkipPythonPackages) {
    Say "  已跳过 (-SkipPythonPackages)"
} else {
    $venv = Join-Path $InstallDir ".venv"
    try {
        if (-not (Test-Path $venv)) { & $py -m venv $venv; Say "  已创建虚拟环境" }
        $vpy = Join-Path $venv "Scripts\python.exe"
        & $vpy -m pip install --upgrade pip --quiet
        # 小助手/取证脚本需要：串口、图片、HTTP、烧写
        & $vpy -m pip install --quiet pyserial pillow requests pyocd
        Say "  已安装: pyserial, pillow, requests, pyocd" "Green"
    } catch {
        Say "  依赖安装失败：$($_.Exception.Message)" "Red"
        Say "  常见原因：网络不通 / 需要代理 / 公司防火墙。" "Yellow"
        Say "  可稍后手动执行：" "Yellow"
        Say "    `"$venv\Scripts\python.exe`" -m pip install pyserial pillow requests pyocd" "DarkGray"
        Say "  （安装继续，小助手可能无法启动）" "Yellow"
    }
}

# ---------- 4. 配置 ----------
Step 4 "生成配置"
$cfgPath = Join-Path $InstallDir "config.json"
$port = $SerialPort
if ($port -eq "auto") {
    $vpy = Join-Path $InstallDir ".venv\Scripts\python.exe"
    if (Test-Path $vpy) {
        $detected = & $vpy -c "import serial.tools.list_ports as p; ps=[x.device for x in p.comports()]; print(ps[0] if ps else '')" 2>$null
        if ($detected) { $port = $detected; Say "  自动识别串口: $port" "Green" }
        else { $port = "COM3"; Say "  未发现串口，先用默认 COM3（之后可在 config.json 改）" "Yellow" }
    } else { $port = "COM3" }
}
$cfg = [ordered]@{
    app           = "titan-mini-pcb-inspector"
    version       = "1.0.0"
    serial_port   = $port
    baudrate      = 115200
    board         = "Titan Board Mini / R7KA8P1KFLC"
    pyocd_target  = "r7ka8p1kf"
    api_endpoint  = "https://api.deepseek.com"
    api_key_file  = "api_key.txt"
    installed_at  = (Get-Date).ToString("s")
}
$cfg | ConvertTo-Json -Depth 4 | Set-Content -Path $cfgPath -Encoding Ascii
Say "  写入 $cfgPath"

# ---------- 5. API Key ----------
Step 5 "大模型 API Key（可选）"
$keyFile = Join-Path $InstallDir "api_key.txt"
if (-not $ApiKey -and -not $Silent) {
    Say "  留空则跳过，云端建议功能不可用（离线规则仍可工作）" "DarkGray"
    $ApiKey = Read-Host "  粘贴你的 API Key（输入不回显）"
}
if ($ApiKey) {
    Set-Content -Path $keyFile -Value $ApiKey.Trim() -NoNewline -Encoding ASCII
    Say "  已写入 api_key.txt（不要提交到任何仓库）" "Green"
} else {
    Say "  跳过"
}

# ---------- 6. 快捷方式 ----------
Step 6 "创建快捷方式"
try {
    $ws = New-Object -ComObject WScript.Shell
    $targets = @(
        @{ name = "AI 小助手";  exe = (Join-Path $InstallDir ".venv\Scripts\pythonw.exe"); args = "`"$(Join-Path $InstallDir 'board_ai_helper.py')`""; dir = $InstallDir },
        @{ name = "AI 服务";    exe = (Join-Path $InstallDir ".venv\Scripts\python.exe");  args = "`"$(Join-Path $InstallDir 'ai_server.py')`"";      dir = $InstallDir }
    )
    $desktop = [Environment]::GetFolderPath("Desktop")
    $startMenu = Join-Path ([Environment]::GetFolderPath("Programs")) $AppName
    New-Item -ItemType Directory -Force -Path $startMenu | Out-Null

    foreach ($t in $targets) {
        if (-not (Test-Path $t.exe)) { Say "  跳过 $($t.name)（解释器不存在）" "DarkYellow"; continue }
        foreach ($dest in @($desktop, $startMenu)) {
            $lnk = $ws.CreateShortcut((Join-Path $dest ("$AppName - " + $t.name + ".lnk")))
            $lnk.TargetPath = $t.exe
            $lnk.Arguments  = $t.args
            $lnk.WorkingDirectory = $t.dir
            $lnk.Description = "$AppName"
            $lnk.Save()
        }
        Say "  已创建: $($t.name)" "Green"
    }
    $unlnk = $ws.CreateShortcut((Join-Path $startMenu "卸载.lnk"))
    $unlnk.TargetPath = "powershell.exe"
    $unlnk.Arguments = "-NoProfile -ExecutionPolicy Bypass -File `"$(Join-Path $InstallDir 'uninstall.ps1')`""
    $unlnk.Save()
} catch {
    Say "  快捷方式创建失败：$($_.Exception.Message)" "Yellow"
    Say "  不影响功能，可直接运行：$InstallDir\board_ai_helper.py" "DarkGray"
}

# ---------- 7. 工具链检查 ----------
Step 7 "工具链检查（只报告，不代装）"
$gcc = Get-Command arm-none-eabi-gcc -ErrorAction SilentlyContinue
if ($gcc) { Say "  arm-none-eabi-gcc: $($gcc.Source)" "Green" }
else {
    Say "  未找到 arm-none-eabi-gcc —— 只能跑 PC 侧小助手，不能编译固件。" "Yellow"
    Say "  下载: https://developer.arm.com/downloads/-/arm-gnu-toolchain-downloads" "DarkGray"
}
$studio = Get-ChildItem "$env:LOCALAPPDATA\RT-ThreadStudio","C:\RT-ThreadStudio" -ErrorAction SilentlyContinue
if ($studio) { Say "  RT-Thread Studio: 已安装" "Green" } else { Say "  RT-Thread Studio: 未检测到（可选）" "DarkGray" }

# ---------- 完成 ----------
Set-Content -Path $Marker -Value (Get-Date).ToString("s") -Encoding ASCII
Write-Host ""
Write-Host "  安装完成" -ForegroundColor Green
Write-Host "  安装目录 : $InstallDir" -ForegroundColor Gray
Write-Host "  配置文件 : $cfgPath" -ForegroundColor Gray
Write-Host "  小助手   : 桌面快捷方式「$AppName - AI 小助手」" -ForegroundColor Gray
Write-Host ""
