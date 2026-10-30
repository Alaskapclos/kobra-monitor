@echo off
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (
  py -3 bootstrap.py --open
) else (
  python bootstrap.py --open
)
if errorlevel 1 pause
