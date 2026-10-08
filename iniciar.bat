@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Execute instalar.bat primeiro.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -c "import sys; assert sys.version_info[:2] == (3,12)" >nul 2>&1
if errorlevel 1 (
  echo Versao incorreta. Este jogo usa Python 3.12. Recrie o ambiente com instalar.bat.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" main.py
if errorlevel 1 pause
