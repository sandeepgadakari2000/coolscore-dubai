@echo off
rem Double-click to run CoolScore Dubai locally. It opens in your browser automatically.
rem Keep the black window open while you use the app; close it to stop the app.
title CoolScore Dubai
cd /d "%~dp0"

rem The Python environment lives outside OneDrive (syncing a venv breaks it).
set "VENV=%USERPROFILE%\.venvs\coolscore"
set "PY=%VENV%\Scripts\python.exe"

if not exist "%PY%" (
    echo First run: setting up Python in %VENV% ^(one time, a few minutes^)...
    py -3.13 -m venv "%VENV%" 2>nul || py -3 -m venv "%VENV%"
    if not exist "%PY%" goto nopython
    "%PY%" -m pip install --upgrade pip
    "%PY%" -m pip install -r requirements.txt
    if errorlevel 1 goto failed
)

echo.
echo   CoolScore Dubai is starting. Your browser will open by itself in a few seconds.
echo   Keep this window open while you use the app. Close it to stop the app.
echo.
"%PY%" tasks.py launch
if errorlevel 1 goto failed
exit /b 0

:nopython
echo.
echo Python 3.11 or newer was not found. Install it from https://www.python.org/downloads/
echo (tick "Add python.exe to PATH"), then double-click this file again.
pause
exit /b 1

:failed
echo.
echo Something went wrong (see the messages above).
pause
exit /b 1
