@echo off
REM ============================================
REM CodeRAG Backend Startup Script (Windows)
REM ============================================

echo ============================================
echo Starting CodeRAG Backend
echo ============================================
echo.

REM Check if Redis is installed
where redis-server >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Redis is not installed or not in PATH!
    echo.
    echo Please install Redis:
    echo 1. Download from: https://github.com/microsoftarchive/redis/releases
    echo 2. Or use Windows Subsystem for Linux (WSL)
    echo 3. Or use Docker: docker run -d -p 6379:6379 redis
    echo.
    pause
    exit /b 1
)

REM Check if Redis is already running
redis-cli ping >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    echo [OK] Redis is already running
) else (
    echo [STARTING] Starting Redis server...
    start /B redis-server
    timeout /t 2 /nobreak >nul
    
    REM Verify Redis started
    redis-cli ping >nul 2>nul
    if %ERRORLEVEL% EQU 0 (
        echo [OK] Redis started successfully
    ) else (
        echo [ERROR] Failed to start Redis
        pause
        exit /b 1
    )
)
echo.

REM Check if virtual environment exists
if not exist ".venv" (
    echo [ERROR] Virtual environment not found!
    echo Please run: python -m venv .venv
    pause
    exit /b 1
)

REM Activate virtual environment
echo [ACTIVATING] Virtual environment...
call .venv\Scripts\activate.bat
echo.

REM Check if .env file exists
if not exist ".env" (
    echo [WARNING] .env file not found!
    echo Please create .env file with your configuration
    echo.
    if exist ".env.example" (
        echo Copying .env.example to .env...
        copy .env.example .env
        echo.
        echo [ACTION REQUIRED] Please edit .env and add your API keys:
        echo - OPENROUTER_API_KEY=your-key-here
        echo.
        notepad .env
        pause
    ) else (
        echo Please create .env file manually
        pause
        exit /b 1
    )
)

REM Create necessary directories
echo [SETUP] Creating directories...
if not exist "logs" mkdir logs
if not exist "chroma_db" mkdir chroma_db
if not exist "%TEMP%\coderag_sessions" mkdir "%TEMP%\coderag_sessions"
echo.

REM Check Python dependencies
echo [CHECK] Checking dependencies...
python -c "import fastapi" 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [INSTALLING] Installing dependencies...
    pip install -r requirements.txt
    echo.
)

REM Display configuration
echo ============================================
echo Configuration:
echo ============================================
python -c "from app.config import settings; print(f'Model: {settings.default_model}'); print(f'Redis: {settings.redis_host}:{settings.redis_port}'); print(f'Embeddings: Local' if settings.use_local_embeddings else 'OpenAI')"
echo ============================================
echo.

REM Start the backend
echo [STARTING] Starting FastAPI backend on port 8000...
echo [INFO] Backend will be available at: http://localhost:8000
echo [INFO] API documentation at: http://localhost:8000/docs
echo [INFO] Press Ctrl+C to stop
echo.
echo ============================================
echo.

REM Start uvicorn
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

REM Cleanup on exit
echo.
echo ============================================
echo Backend stopped
echo ============================================
pause