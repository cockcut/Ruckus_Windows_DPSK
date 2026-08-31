@echo off
setlocal DisableDelayedExpansion
cd /d "%~dp0"
title HSITX Ruckus DPSK Tool - Build EXE
chcp 437 >nul

echo.
echo Build HSITX_Ruckus_DPSK.exe
echo Folder: %CD%
echo.

set "PY="
if exist "%LocalAppData%\Programs\Python\Python312\python.exe" set "PY=%LocalAppData%\Programs\Python\Python312\python.exe"
if not defined PY if exist "%ProgramFiles%\Python312\python.exe" set "PY=%ProgramFiles%\Python312\python.exe"
if not defined PY (
  for /f "delims=" %%I in ('where python 2^>nul') do (
    if not defined PY set "PY=%%I"
  )
)
if not defined PY (
  echo [ERROR] python.exe not found.
  goto END
)

"%PY%" -m pip install "pyinstaller==6.21.0" requests urllib3
if exist dist rmdir /s /q dist
if exist build rmdir /s /q build
if exist HSITX_Ruckus_DPSK.spec del /q HSITX_Ruckus_DPSK.spec

"%PY%" -m PyInstaller --noconfirm --clean --windowed --onefile ^
  --name HSITX_Ruckus_DPSK ^
  --add-data "modules;modules" ^
  --hidden-import requests --hidden-import urllib3 --hidden-import tkinter ^
  gui_app.py

if errorlevel 1 (
  echo [ERROR] PyInstaller failed.
  goto END
)
echo [OK] %CD%\dist\HSITX_Ruckus_DPSK.exe

:END
echo Press any key to close...
pause
endlocal
