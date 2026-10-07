@echo off
chcp 65001 >nul
setlocal
title stepreel
set "VER=0.3.3"
set "HERE=%~dp0"
set "UV=%HERE%bin\uv.exe"
set "MARK=%USERPROFILE%\.stepreel-%VER%"
set "PATH=%USERPROFILE%\.local\bin;%PATH%"
set "UV_HTTP_TIMEOUT=600"

if exist "%MARK%" goto run
if not exist "%UV%" (
  echo 找不到 bin\uv.exe，请重新解压完整的压缩包。
  pause
  exit /b 1
)

echo ==================================================
echo   首次使用：正在安装 stepreel %VER%
echo   需要下载约 1 GB，一般 3 到 15 分钟
echo   请保持联网，不要关闭这个窗口
echo ==================================================

echo.
echo [1/3] 使用清华大学镜像下载 ...
set "UV_DEFAULT_INDEX=https://pypi.tuna.tsinghua.edu.cn/simple"
set "UV_PYTHON_INSTALL_MIRROR=https://mirror.nju.edu.cn/github-release/astral-sh/python-build-standalone"
"%UV%" tool install "%HERE%." --force
if not errorlevel 1 goto ok

echo.
echo [2/3] 清华镜像失败，改用阿里云镜像 ...
set "UV_DEFAULT_INDEX=https://mirrors.aliyun.com/pypi/simple"
set "UV_PYTHON_INSTALL_MIRROR="
"%UV%" tool install "%HERE%." --force
if not errorlevel 1 goto ok

echo.
echo [3/3] 国内镜像失败，改用官方源 ...
set "UV_DEFAULT_INDEX="
"%UV%" tool install "%HERE%." --force
if not errorlevel 1 goto ok

echo.
echo ==================================================
echo   安装失败。请检查网络后重新双击本文件，
echo   已下载的部分会保留，不会从头再来。
echo   如果多次失败，请把这个窗口截图发给作者。
echo ==================================================
pause
exit /b 1

:ok
echo ok> "%MARK%"
echo 安装完成。

:run
echo 正在打开界面，浏览器会自动弹出。使用期间请不要关闭这个窗口。
stepreel ui
if errorlevel 1 pause
