@echo off
REM Manual cleanup script for CodeRAG sessions

echo ============================================
echo CodeRAG Manual Cleanup
echo ============================================
echo.

REM Clean temporary sessions
echo Cleaning temporary session files...

REM Try Windows temp
if exist "%TEMP%\coderag_sessions" (
    echo Found sessions in TEMP directory
    rmdir /S /Q "%TEMP%\coderag_sessions" 2>nul
    if exist "%TEMP%\coderag_sessions" (
        echo [WARNING] Some files may be locked. Trying force cleanup...
        rd /s /q "%TEMP%\coderag_sessions"
    )
    echo [OK] Cleaned TEMP sessions
)

REM Try /tmp (WSL or Cygwin)
if exist "C:\tmp\coderag_sessions" (
    echo Found sessions in /tmp directory
    rmdir /S /Q "C:\tmp\coderag_sessions" 2>nul
    echo [OK] Cleaned /tmp sessions
)

REM Clean ChromaDB
if exist "chroma_db" (
    echo Cleaning ChromaDB...
    rmdir /S /Q "chroma_db" 2>nul
    if not exist "chroma_db" (
        echo [OK] ChromaDB cleaned
    )
)

REM Clean logs (optional)
echo.
set /p clean_logs="Do you want to clean logs? (y/n): "
if /i "%clean_logs%"=="y" (
    if exist "logs" (
        del /Q logs\*.log 2>nul
        echo [OK] Logs cleaned
    )
)

REM Flush Redis (optional)
echo.
set /p flush_redis="Do you want to flush Redis database? (y/n): "
if /i "%flush_redis%"=="y" (
    echo Flushing Redis...
    redis-cli FLUSHDB
    if %ERRORLEVEL% EQU 0 (
        echo [OK] Redis flushed
    ) else (
        echo [WARNING] Redis not available or already empty
    )
)

echo.
echo ============================================
echo Cleanup completed!
echo ============================================
echo.
pause