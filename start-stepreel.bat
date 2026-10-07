@echo off
chcp 65001 >nul
title stepreel
echo 正在启动 stepreel，第一次运行会自动安装（约 1 GB，需要几分钟）...
set "PATH=%USERPROFILE%\.local\bin;%PATH%"
where uv >nul 2>nul
if errorlevel 1 (
  echo 安装 uv ...
  powershell -ExecutionPolicy ByPass -NoProfile -Command "irm https://astral.sh/uv/install.ps1 | iex"
  set "PATH=%USERPROFILE%\.local\bin;%PATH%"
)
where stepreel >nul 2>nul
if errorlevel 1 (
  echo 安装 stepreel ...
  uv tool install "%~dp0."
)
stepreel ui
pause
