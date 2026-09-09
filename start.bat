@echo off
REM ==========================================================
REM start.bat — авто-деплой и запуск проекта db_manager / api.
REM Шаги: стоп процессов -> очистка кэша -> установка -> тесты -> запуск API
REM ==========================================================
setlocal ENABLEDELAYEDEXPANSION

cd /d "%~dp0"

echo [1/5] Stopping previous python processes on this project...
for /f "tokens=*" %%P in ('wmic process where "name='python.exe'" get ProcessId 2^>nul ^| findstr /R "^[0-9]"') do (
    echo   killing PID %%P
    taskkill /F /PID %%P >nul 2>&1
)

echo [2/5] Cleaning __pycache__ and *.pyc...
for /d /r "%cd%" %%D in (__pycache__) do (
    if exist "%%D" rd /s /q "%%D"
)
del /s /q "%cd%\*.pyc" >nul 2>&1

echo [3/5] Installing dependencies...
python -m pip install --upgrade pip >nul
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo   pip install failed; trying minimal set...
    python -m pip install bcrypt flask pytest
)

echo [4/5] Syntax / smoke checks...
python -m compileall db_manager api utils.py wsgi.py >nul
if errorlevel 1 (
    echo   Syntax errors detected! Aborting.
    exit /b 1
)
python -m pytest tests -q
if errorlevel 1 (
    echo   Tests failed! Aborting start.
    exit /b 1
)

echo [5/5] Starting API on %API_HOST%:%API_PORT% ...
if "%API_DEBUG%"=="1" set API_DEBUG=1
python wsgi.py

endlocal