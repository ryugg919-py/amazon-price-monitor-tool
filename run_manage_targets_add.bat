@echo off
cd /d "%~dp0"

:: --- Activate your virtual environment ---
call .venv\Scripts\activate

:: --- Run the command ---
python -m src.manage_targets add

pause
