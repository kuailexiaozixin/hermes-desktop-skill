@echo off
rem 业务系统 独立启动（纯业务，不含 Agent 对话）
rem 用法：双击本文件；或命令行 `启动.bat`
cd /d "%~dp0"
set PYTHONHOME=
set PYTHONPATH=
set RD_BIZ_STANDALONE=1
python app.py
pause
