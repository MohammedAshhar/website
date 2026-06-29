@echo off
cd /d %~dp0
echo === Unicus Diagnostics - Starting ===
echo.
echo Step 1: Starting Cassandra (Docker)...
docker compose -f DataBase\docker-compose.unicus.yml up -d cassandra
if %errorlevel% neq 0 (
    echo [ERROR] Docker not found or failed. Install Docker Desktop: https://docs.docker.com/desktop/setup/install/windows-install/
    pause
    exit /b 1
)
echo.
echo Step 2: Waiting for Cassandra to be ready (may take 1-2 min first time)...
:wait_loop
timeout /t 10 /nobreak >nul
docker ps --filter name=unicus-cassandra --format "{{.Status}}" | findstr "(healthy)" >nul
if errorlevel 1 goto wait_loop
echo Cassandra is healthy!
echo.
echo Step 3: Starting Unicus Backend...
cd DataBase
pip install -r requirements.txt >nul 2>&1
python -m unicus_lims
if %errorlevel% neq 0 (
    echo [ERROR] Python or dependencies missing. Install Python 3.10+ from python.org
    pause
)
pause
