@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Execute instalar.bat primeiro.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -m pip install -r requirements-dev.txt -c constraints.txt
if errorlevel 1 exit /b 1
".venv\Scripts\python.exe" -m pytest tests -q
pause
