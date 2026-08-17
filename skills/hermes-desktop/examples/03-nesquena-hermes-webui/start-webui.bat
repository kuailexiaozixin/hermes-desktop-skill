@echo off
setlocal
cd /d "%~dp0"

REM Clear inherited Python env pollution (PYTHONHOME/PYTHONPATH) so the
REM bundled python.exe uses its own standard library & site-packages.
set "PYTHONHOME="
set "PYTHONPATH="

set "HERMES_WEBUI_AGENT_DIR=D:\临时环境\hermes-desktop-01\Lib\site-packages"
set "PYTHON=D:\临时环境\hermes-desktop-01\Scripts\python.exe"

echo [start-webui] Hermes WebUI launcher
echo [start-webui] Python : %PYTHON%
echo [start-webui] Agent  : %HERMES_WEBUI_AGENT_DIR%
echo [start-webui] Open   : http://localhost:8787  (press Ctrl+C to stop)
echo.
"%PYTHON%" server.py
echo.
pause
