@echo off
REM ==========================================================
REM start.bat — авто-деплой и запуск go-server (cmd/server).
REM Шаги: stop -> clean -> build -> test -> run
REM ==========================================================
setlocal ENABLEDELAYEDEXPANSION

cd /d "%~dp0"

echo [1/4] Stopping previous processes on this project...
for /f "tokens=*" %%P in ('wmic process where "name='go-server.exe'" get ProcessId 2^>nul ^| findstr /R "^[0-9]"') do (
    echo   killing PID %%P
    taskkill /F /PID %%P >nul 2>&1
)

echo [2/4] Cleaning caches and binaries...
if exist bin rmdir /s /q bin
del /s /q *.exe >nul 2>&1

echo [3/4] Building...
where go >nul 2>&1
if errorlevel 1 (
    echo   Go is not installed. Install from https://go.dev/dl/
    exit /b 1
)
go mod tidy
if errorlevel 1 (
    echo   go mod tidy failed
    exit /b 1
)
go build -o bin\go-server.exe ./cmd/server
if errorlevel 1 (
    echo   go build failed
    exit /b 1
)

echo [4/4] Running tests and server...
go test ./tests/... -v
if errorlevel 1 (
    echo   tests failed
    exit /b 1
)
echo starting server on %API_HOST%:%API_PORT% ...
bin\go-server.exe

endlocal