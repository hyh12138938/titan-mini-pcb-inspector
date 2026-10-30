@echo off
cd /d "%~dp0"
rem WebView build: stdlib backend on 127.0.0.1:8765 + Edge/Chrome app window.
rem Fallback for debugging: python server.py   (shows the console + tracebacks)
start "" pythonw server.py
exit /b
