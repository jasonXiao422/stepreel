@echo off
chcp 65001 >nul
title stepreel
set "VER=0.3.0"
set "MARK=%USERPROFILE%\.stepreel-%VER%"
set "PATH=%USERPROFILE%\.local\bin;%PATH%"

where uv >nul 2>nul
if errorlevel 1 (
  echo 第一次使用，正在安装 uv ...
  powershell -ExecutionPolicy ByPass -NoProfile -Command "irm https://astral.sh/uv/install.ps1 | iex"
  set "PATH=%USERPROFILE%\.local\bin;%PATH%"
)

if not exist "%MARK%" (
  echo 正在安装 stepreel %VER%，第一次需要下载约 1 GB，请耐心等几分钟 ...
  uv tool install "%~dp0." --force
  if errorlevel 1 (
    echo 安装失败，请把上面的报错截图发给开发者。
    pause
    exit /b 1
  )
  echo ok> "%MARK%"
)

echo 正在打开界面，浏览器会自动弹出。使用期间请不要关闭这个窗口。
stepreel ui
pause
