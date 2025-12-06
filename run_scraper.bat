@echo off
REM ============================================
REM  Amazon Price Monitor - Run Script
REM  1. Change directory to project root
REM  2. Activate virtual environment (.venv)
REM  3. Run main script (python -m src.main)
REM ============================================

REM Go to this script's directory
cd /d "%~dp0"

REM Activate virtual environment
call ".venv\Scripts\activate.bat"

REM Run scraper
python -m src.main

REM Finish message
echo.
echo --------------------------------------------
echo Run finished. Please check the logs folder.
echo Press any key to close this window.
echo --------------------------------------------
pause > nul
