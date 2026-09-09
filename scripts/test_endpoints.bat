@echo off
REM ==========================================================
REM scripts/test_endpoints.bat — Windows-обёртка над test_endpoints.sh
REM Проверяет эндпоинты через curl.
REM
REM Использование:
REM   scripts\test_endpoints.bat
REM   set BASE_URL=http://server:5000 ^&^& scripts\test_endpoints.bat
REM ==========================================================
setlocal

if "%BASE_URL%"=="" set "BASE_URL=http://127.0.0.1:5000"

where curl >nul 2>&1
if errorlevel 1 (
    echo [ERROR] curl not found. Install via Git for Windows or Windows 10+ 1803.
    exit /b 1
)

if "%CONTAINER%"=="" (
    echo Container: ^(none^)
) else (
    echo Container: %CONTAINER%
)

echo BASE_URL = %BASE_URL%
echo ------------------------------------------------------------

set /a PASS=0
set /a FAIL=0

REM --- helper: run_curl ---
REM %1=label %2=expected %3=method %4=path %5=body (optional)
:run_curl
set "LABEL=%~1"
set "EXPECT=%~2"
set "METHOD=%~3"
set "PATH_=%~4"
set "BODY=%~5"

if "%BODY%"=="" (
    for /f "delims=" %%C in ('curl -sS -o NUL -w "%%{http_code}" -X %METHOD% "%BASE_URL%%PATH_%"') do set "CODE=%%C"
) else (
    for /f "delims=" %%C in ('curl -sS -o NUL -w "%%{http_code}" -X %METHOD% "%BASE_URL%%PATH_%" -H "Content-Type: application/json" -d "%BODY%"') do set "CODE=%%C"
)

if "%CODE%"=="%EXPECT%" (
    echo [OK] %LABEL%  [%METHOD% %PATH_%%] expected=%EXPECT% got=%CODE%
    set /a PASS+=1
) else (
    echo [FAIL] %LABEL%  [%METHOD% %PATH_%%] expected=%EXPECT% got=%CODE%
    set /a FAIL+=1
)
goto :eof

REM --- вызовы ---
call :run_curl "healthcheck"        200 GET  "/health"
call :run_curl "create alice"        201 POST "/users" "{\"name\":\"alice\",\"tags\":[\"vip\"]}"
call :run_curl "create bob"          201 POST "/users" "{\"name\":\"bob\",\"tags\":[]}"
call :run_curl "duplicate alice"     409 POST "/users" "{\"name\":\"alice\"}"
call :run_curl "empty name"          422 POST "/users" "{\"name\":\"\"}"
call :run_curl "get user #1"         200 GET  "/users/1"
call :run_curl "user not found"      404 GET  "/users/9999"
call :run_curl "invalid id"          404 GET  "/users/abc"
call :run_curl "list users"          200 GET  "/users"
call :run_curl "set password #1"     201 POST "/users/1/password" "{\"password\":\"hunter2\"}"
call :run_curl "empty password"      422 POST "/users/1/password" "{\"password\":\"\"}"
call :run_curl "set password no-user" 404 POST "/users/9999/password" "{\"password\":\"x\"}"
call :run_curl "active users"        200 GET  "/active"

echo ------------------------------------------------------------
if %FAIL%==0 (
    echo [OK] All %PASS% checks passed.
    exit /b 0
) else (
    echo [FAIL] %FAIL%/%PASS%+%FAIL% checks FAILED.
    exit /b 1
)