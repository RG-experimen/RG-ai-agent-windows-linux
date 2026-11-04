@echo off
REM Launch script for Multi-Provider AI Agent (Windows)
title Multi-Provider AI Agent v2.0

cd /d "%~dp0"
echo ============================================================
echo  Starting Multi-Provider AI Agent v2.0...
echo ============================================================

where python >nul 2>nul
if %ERRORLEVEL% equ 0 (
    python agent.py %*
    goto end
)

where py >nul 2>nul
if %ERRORLEVEL% equ 0 (
    py agent.py %*
    goto end
)

echo Error: Python was not found in PATH. Please install Python 3.9+ from python.org.
pause

:end
