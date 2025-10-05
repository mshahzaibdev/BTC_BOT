@echo off
echo ====================================
echo  ICT Trading Signal Discord Bot
echo ====================================
echo.

REM Check if venv exists
if not exist "venv\" (
    echo Creating virtual environment...
    python -m venv venv
    echo.
)

echo Activating virtual environment...
call venv\Scripts\activate
echo.

echo Installing/Updating dependencies...
pip install -r requirements_bot.txt
echo.

echo Starting bot...
echo.
python bot.py

pause
