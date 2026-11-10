@echo off
chcp 65001 >nul
title AutoVideo Studio - Instalacao
cd /d "%~dp0"
echo ============================================
echo   AutoVideo Studio - Instalacao
echo ============================================
echo.
where py >nul 2>nul
if %errorlevel%==0 (set PY=py -3) else (set PY=python)
%PY% --version >nul 2>nul
if not %errorlevel%==0 (
  echo [!] Python nao encontrado.
  echo     Instale o Python 3.12.10 em https://www.python.org/downloads/
  echo     IMPORTANTE: marque a opcao "Add python.exe to PATH" na instalacao.
  pause
  exit /b
)
echo [1/4] Criando ambiente...
if not exist .venv\Scripts\python.exe %PY% -m venv .venv
call .venv\Scripts\activate.bat
echo [2/4] Instalando bibliotecas...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
echo.
echo [3/4] Verificando FFmpeg...
where ffmpeg >nul 2>nul
if not %errorlevel%==0 (
  echo FFmpeg nao encontrado. Tentando instalar com o winget...
  winget install -e --id Gyan.FFmpeg --accept-source-agreements --accept-package-agreements
  echo.
  echo Se o winget falhou: baixe o FFmpeg em https://www.gyan.dev/ffmpeg/builds/
  echo  ^(ffmpeg-release-full.7z^), extraia e informe a pasta "bin" na tela de configuracoes do programa.
) else (
  echo FFmpeg OK.
)
echo.
echo [4/4] Criando atalhos na Area de Trabalho e no menu Iniciar...
python criar_atalhos.py
echo.
set /p WH=Instalar legendas com sincronia palavra-por-palavra (faster-whisper, ~500MB)? [s/N]: 
if /i "%WH%"=="s" python -m pip install faster-whisper
echo.
echo ============================================
echo  Pronto! Abra pelo icone "AutoVideo Studio"
echo  na Area de Trabalho ou no menu Iniciar.
echo  (o ABRIR.bat continua funcionando, para ver erros)
echo ============================================
pause
