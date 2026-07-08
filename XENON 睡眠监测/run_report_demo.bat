@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo.
echo XENON local demo - SNORE.CSV in this folder
echo.

if not exist "%~dp0SNORE.CSV" (
  echo [ERROR] SNORE.CSV not found in:
  echo %~dp0
  pause
  exit /b 1
)

where py >nul 2>&1
if not errorlevel 1 (
  py -3 -c "import matplotlib" >nul 2>&1 || py -3 -m pip install matplotlib -q
  py -3 "%~dp0snore.py" --input "%~dp0SNORE.CSV" --out-dir "%~dp0report"
  if not errorlevel 1 goto success
)

where python >nul 2>&1
if not errorlevel 1 (
  python -c "import matplotlib" >nul 2>&1 || python -m pip install matplotlib -q
  python "%~dp0snore.py" --input "%~dp0SNORE.CSV" --out-dir "%~dp0report"
  if not errorlevel 1 goto success
)

echo [ERROR] Python not found or report failed.
pause
exit /b 1

:success
echo Report folder: %~dp0report
start "" "%~dp0report"
pause
endlocal
