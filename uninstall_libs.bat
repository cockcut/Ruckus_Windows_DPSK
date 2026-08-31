@echo off
setlocal DisableDelayedExpansion
cd /d "%~dp0"
title HSITX Ruckus DPSK Tool - Uninstall
chcp 437 >nul
echo Uninstall DPSK pip packages? [Y/N]
set /p ASK=
if /I not "%ASK%"=="Y" goto END
set "PYDIR=%LocalAppData%\Programs\Python\Python312"
set "PY="
if exist "%PYDIR%\python.exe" set "PY=%PYDIR%\python.exe"
if defined PY (
  "%PY%" -m pip uninstall -y requests urllib3
)
echo Done. Python itself is not removed.
:END
pause
endlocal
