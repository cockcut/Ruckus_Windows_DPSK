@echo off
setlocal DisableDelayedExpansion
cd /d "%~dp0"
title HSITX Ruckus DPSK Tool
chcp 437 >nul

echo.
echo ============================================================
echo   HSITX Ruckus DPSK Tool
echo ============================================================
echo.
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

if defined PY goto PYTHON_OK

echo [INFO] Python 3.12 not found. Install now? [Y/N]
set /p ASKPY=
if /I not "%ASKPY%"=="Y" goto CANCEL
where winget >nul 2>&1
if errorlevel 1 (
    echo [ERROR] winget not found.
    goto END
)
echo [*] winget install Python 3.12 ...
winget install --id Python.Python.3.12 --source winget --scope user --accept-package-agreements --accept-source-agreements
if exist "%LocalAppData%\Programs\Python\Python312\python.exe" set "PY=%LocalAppData%\Programs\Python\Python312\python.exe"
if not defined PY if exist "%ProgramFiles%\Python312\python.exe" set "PY=%ProgramFiles%\Python312\python.exe"
if not defined PY (
    echo [ERROR] python.exe not found after install.
    goto END
)

:PYTHON_OK
echo [OK] Python found.
echo     %PY%
"%PY%" --version
echo.

echo [*] Checking libraries...
"%PY%" -c "import requests" >nul 2>&1
if not errorlevel 1 goto LIBS_OK
echo [*] Installing requests ...
"%PY%" -m pip --version >nul 2>&1
if errorlevel 1 "%PY%" -m ensurepip --upgrade
"%PY%" -m pip install --upgrade pip
"%PY%" -m pip install -r requirements.txt
"%PY%" -c "import requests" >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Library install failed.
    goto END
)

:LIBS_OK
echo [OK] Libraries ready.
echo.
if not exist "gui_app.py" (
    echo [ERROR] gui_app.py not found.
    goto END
)
echo Starting GUI...
"%PY%" gui_app.py
set "EXITCODE=%ERRORLEVEL%"
echo.
if "%EXITCODE%"=="0" echo Program finished OK.
if not "%EXITCODE%"=="0" echo Program exited with code %EXITCODE%
goto END

:CANCEL
echo Canceled.

:END
echo.
echo Press any key to close...
pause
endlocal
