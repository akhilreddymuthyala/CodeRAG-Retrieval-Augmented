@echo off
REM ============================================
REM Redis Startup Script (Windows)
REM ============================================

echo ============================================
echo Starting Redis Server
echo ============================================
echo.

REM Check if Redis is installed
where redis-server >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Redis is not installed or not in PATH!
    echo.
    echo === Installation Options ===
    echo.
    echo Option 1: Download Redis for Windows
    echo   https://github.com/microsoftarchive/redis/releases
    echo   Download: Redis-x64-3.0.504.msi
    echo.
    echo Option 2: Use Windows Subsystem for Linux (WSL)
    echo   wsl --install
    echo   wsl
    echo   sudo apt install redis-server
    echo   redis-server
    echo.
    echo Option 3: Use Docker
    echo   docker run -d -p 6379:6379 --name redis redis
    echo.
    echo Option 4: Use Memurai (Redis-compatible for Windows)
    echo   https://www.memurai.com/get-memurai
    echo.
    pause
    exit /b 1
)

REM Check if Redis is already running
redis-cli ping >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    echo [OK] Redis is already running!
    echo.
    redis-cli INFO server | findstr "redis_version"
    echo.
    echo Redis is ready at: localhost:6379
    echo.
    pause
    exit /b 0
)

REM Start Redis
echo [STARTING] Starting Redis server...
echo.
echo Redis will be available at: localhost:6379
echo Press Ctrl+C to stop Redis
echo.
echo ============================================
echo.

REM Start Redis server (foreground mode)
redis-server

REM If Redis exits
echo.
echo ============================================
echo Redis stopped
echo ============================================
pause