@echo off
chcp 65001 >nul
title Titan Mini PCB Inspector - Install

echo.
echo   Titan Mini PCB Inspector
echo   starting installer...
echo.

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1" %*

if errorlevel 1 (
    echo.
    echo   [FAILED] see the red lines above.
) else (
    echo.
    echo   [DONE] press any key to close.
)
pause >nul
