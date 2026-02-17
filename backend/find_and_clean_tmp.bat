@echo off
REM Find and cleanup /tmp directory on Windows

echo ============================================
echo Finding /tmp directory on Windows
echo ============================================
echo.

REM Check common locations for /tmp on Windows
set FOUND=0

REM Location 1: C:\tmp
if exist "C:\tmp\coderag_sessions" (
    echo [FOUND] C:\tmp\coderag_sessions
    set FOUND=1
    rmdir /S /Q "C:\tmp\coderag_sessions" 2>nul
    if not exist "C:\tmp\coderag_sessions" (
        echo [OK] Deleted C:\tmp\coderag_sessions
    ) else (
        echo [ERROR] Failed to delete C:\tmp\coderag_sessions
    )
)

REM Location 2: System Temp
if exist "%TEMP%\coderag_sessions" (
    echo [FOUND] %TEMP%\coderag_sessions
    set FOUND=1
    rmdir /S /Q "%TEMP%\coderag_sessions" 2>nul
    if not exist "%TEMP%\coderag_sessions" (
        echo [OK] Deleted %TEMP%\coderag_sessions
    ) else (
        echo [ERROR] Failed to delete %TEMP%\coderag_sessions
    )
)

REM Location 3: User Temp
if exist "%USERPROFILE%\AppData\Local\Temp\coderag_sessions" (
    echo [FOUND] %USERPROFILE%\AppData\Local\Temp\coderag_sessions
    set FOUND=1
    rmdir /S /Q "%USERPROFILE%\AppData\Local\Temp\coderag_sessions" 2>nul
)

REM Location 4: Git Bash /tmp (if using Git for Windows)
if exist "%PROGRAMFILES%\Git\tmp\coderag_sessions" (
    echo [FOUND] %PROGRAMFILES%\Git\tmp\coderag_sessions
    set FOUND=1
    rmdir /S /Q "%PROGRAMFILES%\Git\tmp\coderag_sessions" 2>nul
)

REM Location 5: Search in all drives
echo.
echo Searching all drives for coderag_sessions...
for %%d in (C D E F) do (
    if exist "%%d:\tmp\coderag_sessions" (
        echo [FOUND] %%d:\tmp\coderag_sessions
        set FOUND=1
        rmdir /S /Q "%%d:\tmp\coderag_sessions" 2>nul
    )
)

if %FOUND%==0 (
    echo.
    echo [INFO] No coderag_sessions directories found
    echo.
    echo The /tmp path on Windows could be mapped to:
    echo - C:\tmp
    echo - %TEMP% = %TEMP%
    echo - %USERPROFILE%\AppData\Local\Temp
    echo.
    echo Your .env has: TEMP_FOLDER=/tmp/coderag_sessions
    echo On Windows this likely means: C:\tmp\coderag_sessions
)

echo.
echo ============================================
echo Cleanup complete
echo ============================================
pause