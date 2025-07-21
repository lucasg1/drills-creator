@echo off
echo Starting Hand Image Server...
echo.

REM Check if Docker is running
docker version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Docker is not running or not installed.
    echo Please start Docker Desktop and try again.
    pause
    exit /b 1
)

echo Docker is running. Building and starting the container...
echo.

REM Stop and remove any existing container
docker stop hand-image-server >nul 2>&1
docker rm hand-image-server >nul 2>&1

REM Build the image
echo Building Docker image...
docker build -t hand-image-server .

if %errorlevel% neq 0 (
    echo ERROR: Failed to build Docker image.
    pause
    exit /b 1
)

REM Start the container
echo Starting container...
docker run -p 8777:8777 --name hand-image-server hand-image-server

echo.
echo Server stopped. Cleaning up...
docker rm hand-image-server >nul 2>&1
echo Press any key to exit...
pause >nul 