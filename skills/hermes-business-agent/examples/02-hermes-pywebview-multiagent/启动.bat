@echo off
cd /d "%~dp0"
set PYTHONHOME=
title Hermes Desktop - 02-hermes-pywebview-multiagent

set VENV=D:\临时环境\hermes-desktop-02
set PYEXE=%VENV%\Scripts\python.exe

if not exist "%PYEXE%" (
    echo [首次运行] 创建全局虚拟环境 hermes-desktop-02 ...
    python -m venv "%VENV%"
    "%PYEXE%" -m pip install --upgrade pip -q
    "%PYEXE%" -m pip install -r "%~dp0requirements.txt"
    if errorlevel 1 (
        echo [错误] 依赖安装失败，请检查网络后重试。
        pause
        exit /b 1
    )
)

echo [启动] python app.py ...
"%PYEXE%" app.py
if errorlevel 1 pause
