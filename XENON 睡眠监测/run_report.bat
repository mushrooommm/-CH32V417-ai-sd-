@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo.
echo ========================================
echo   XENON Sleep Monitor - Report Generator
echo ========================================
echo.

set "CSV_FILE="
for %%d in (E F G H I J D) do (
  if exist "%%d:\SNORE.CSV" (
    set "CSV_FILE=%%d:\SNORE.CSV"
    goto found_usb
  )
)
:found_usb

if not defined CSV_FILE (
  if exist "%~dp0SNORE.CSV" set "CSV_FILE=%~dp0SNORE.CSV"
)

if not defined CSV_FILE (
  echo [WARN] SNORE.CSV not found on USB or in this folder.
  echo.
  set /p "CSV_FILE=Enter full path to SNORE.CSV: "
)

if "%CSV_FILE%"=="" (
  echo [ERROR] No input file specified.
  pause
  exit /b 1
)

if not exist "%CSV_FILE%" (
  echo [ERROR] File not found: %CSV_FILE%
  pause
  exit /b 1
)

echo [1/3] Input: %CSV_FILE%
echo [2/3] Generating charts...
echo.

where py >nul 2>&1
if not errorlevel 1 (
  py -3 -c "import matplotlib" >nul 2>&1 || py -3 -m pip install matplotlib -q
  py -3 "%~dp0snore.py" --input "%CSV_FILE%" --out-dir "%~dp0report"
  if not errorlevel 1 goto success
)

where python >nul 2>&1
if not errorlevel 1 (
  python -c "import matplotlib" >nul 2>&1 || python -m pip install matplotlib -q
  python "%~dp0snore.py" --input "%CSV_FILE%" --out-dir "%~dp0report"
  if not errorlevel 1 goto success
)

echo [ERROR] Python not found or report failed.
echo Install Python 3, then: pip install matplotlib
pause
exit /b 1

:success
echo.
echo [3/3] Done.
echo Report folder: %~dp0report
start "" "%~dp0report"
pause
endlocal
