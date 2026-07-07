@echo off
setlocal enabledelayedexpansion

title cmd_sender Builder

set "SCRIPT_DIR=%~dp0"
set "SCRIPT_NAME=cmd_sender.py"
set "OUTPUT_DIR=%SCRIPT_DIR%dist"

echo ============================================
echo   cmd_sender Builder (PyInstaller)
echo ============================================
echo.

:: Check Python
where python.exe >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python not found. Please install Python 3.10+ and add to PATH.
    pause
    exit /b 1
)

:: Show Python version
for /f "tokens=*" %%i in ('python --version 2^>nul') do set "PY_VER=%%i"
echo   Using: %PY_VER%

:: Check / Install PyInstaller
echo.
echo [1/3] Checking dependencies...
pip show pyinstaller >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo   - PyInstaller not found, installing...
    pip install pyinstaller
    if %ERRORLEVEL% NEQ 0 (
        echo [ERROR] Failed to install PyInstaller.
        pause
        exit /b 1
    )
) else (
    echo   - PyInstaller is ready
)

:: Change to script directory
cd /d "%SCRIPT_DIR%"

:: Check script exists
if not exist "%SCRIPT_NAME%" (
    echo [ERROR] %SCRIPT_NAME% not found in %SCRIPT_DIR%
    pause
    exit /b 1
)

:: Build with PyInstaller
echo.
echo [2/3] Building EXE (this may take a few minutes)...
echo.
pyinstaller --onefile --windowed --name cmd_sender --clean "%SCRIPT_NAME%"
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Build failed. Check errors above.
    pause
    exit /b 1
)

:: Done
echo.
echo [3/3] Build complete!
echo.
echo   Output: %OUTPUT_DIR%\cmd_sender.exe
if exist "%OUTPUT_DIR%\cmd_sender.exe" (
    for %%f in ("%OUTPUT_DIR%\cmd_sender.exe") do echo   Size: %%~zf bytes
)
echo.
echo ============================================
echo   Run %OUTPUT_DIR%\cmd_sender.exe directly.
echo   No Python environment needed.
echo ============================================
echo.

:: Ask to open output folder
set "OPEN_DIR="
set /p "OPEN_DIR=Open output folder? (Y/n): "
if /i "!OPEN_DIR!"=="" set "OPEN_DIR=Y"
if /i "!OPEN_DIR!"=="Y" (
    if exist "%OUTPUT_DIR%" (
        explorer "%OUTPUT_DIR%"
    )
)

pause
