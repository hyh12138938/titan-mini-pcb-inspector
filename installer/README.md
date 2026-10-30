# 一键安装包（PC 侧）

这个目录负责把「电脑上跑的那套东西」装到任意一台 Windows 上：**Python 依赖 + pyocd + AI 小助手 + 板级取证脚本 + 配置 + 快捷方式**。

## 产物

```
dist/Titan-Mini-PCB-Inspector-Installer-v1.0.0.zip
```

解压后双击 **`install.cmd`** 即可。默认装到 `%LOCALAPPDATA%\TitanPcbInspector`。

## 它做了什么

| 步骤 | 动作 |
|---|---|
| 1 | 检查 Python ≥ 3.9（没有就提示安装方式，不替你装） |
| 2 | 复制小助手与脚本到安装目录 |
| 3 | 建 venv，装 `pyserial` / `pillow` / `requests` / `pyocd` |
| 4 | 自动识别串口，写 `config.json`（波特率 115200、pyocd target `r7ka8p1kf`） |
| 5 | 询问大模型 API Key，写到本地 `api_key.txt`（留空则跳过） |
| 6 | 建桌面 + 开始菜单快捷方式，以及「卸载」 |
| 7 | 检查 `arm-none-eabi-gcc` 与 RT-Thread Studio，**只报告不代装** |

## 它不做什么（很重要）

1. **不装 ARM 工具链**（~300 MB）——给下载地址，你自己装。
2. **不装 RT-Thread Studio**（官方安装包 1.3 GB）——它有自己的安装器，包办会互相打架。
3. **不下载 SDK**——仓库里只有补丁，SDK 从 gitee 上游 clone。
4. **不代填 API Key**——安装时输入，只写本地，永不进仓库。

也就是说：**装完能立刻用 PC 侧小助手（看图 / 串口 / 拍照回传 / 烧写），想编译固件还得补工具链。**

## 静默安装

```powershell
.\install.ps1 -Silent -ApiKey "sk-xxxx" -SerialPort COM5
```

| 参数 | 说明 |
|---|---|
| `-InstallDir` | 自定义安装目录 |
| `-Silent` | 不提问 |
| `-ApiKey` | 直接写入密钥 |
| `-SerialPort` | 指定串口，默认 `auto` 自动探测 |
| `-SkipPythonPackages` | 跳过 pip（离线环境或已装好） |

## 卸载

开始菜单「卸载」，或：

```powershell
.\uninstall.ps1                # 全删
.\uninstall.ps1 -KeepConfig    # 保留 config.json 与 api_key.txt
```

## 自己重新打包

```bash
python installer/build_installer.py
```

会把 `tools/helper`、`tools/board-scripts` 收进 `payload/`，与两个安装脚本一起压成 zip。
