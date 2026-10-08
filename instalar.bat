@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
echo.
echo B7 GAMES INTERATIVOS - Instalacao do Voxel Live
echo.
py -3.12 -c "import sys; assert sys.version_info[:2] == (3,12) and sys.maxsize > 2**32" >nul 2>&1
if errorlevel 1 (
  echo Python 3.12 nao encontrado. Instale o Python 3.12 de 64 bits.
  echo Marque Python Launcher e Add Python to PATH no instalador.
  echo Download: https://www.python.org/downloads/release/python-31210/
  echo Este instalador nao usara o Python 3.14.
  pause
  exit /b 1
)
if not exist ".venv\Scripts\python.exe" (
  py -3.12 -m venv .venv
  if errorlevel 1 goto :erro
)
".venv\Scripts\python.exe" -c "import sys; assert sys.version_info[:2] == (3,12) and sys.maxsize > 2**32" >nul 2>&1
if errorlevel 1 (
  echo O ambiente .venv pertence a outra versao do Python. Renomeie a pasta .venv e tente novamente.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 goto :erro
".venv\Scripts\python.exe" -m pip install -r requirements.txt -c constraints.txt
if errorlevel 1 goto :erro
".venv\Scripts\python.exe" -c "import pygame,fastapi,uvicorn; from TikTokLive import TikTokLiveClient; from TikTokLive.client.web.web_settings import WebDefaults; print('Dependencias verificadas.')"
if errorlevel 1 goto :erro
echo.
echo Instalacao concluida. Abra iniciar.bat.
pause
exit /b 0
:erro
echo.
echo A instalacao falhou. Confira a internet e a mensagem acima.
pause
exit /b 1
