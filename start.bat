@echo off
rem ============================================================
rem  MCU Debug Assistant 一键启动
rem  双击本文件即可打开调试助手（Windows）
rem
rem  依赖：
rem    Python 3.10+（已加入 PATH）
rem    库安装：python -m pip install -r requirements.txt
rem ============================================================
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
    echo [错误] 未找到 Python，请先安装 Python 3.10+ 并加入 PATH。
    pause
    exit /b 1
)

python -m desktop.main
if errorlevel 1 (
    echo.
    echo [提示] 启动失败。请检查依赖是否安装：
    echo        python -m pip install -r requirements.txt
    pause
)
