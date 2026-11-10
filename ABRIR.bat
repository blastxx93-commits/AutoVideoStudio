@echo off
chcp 65001 >nul
title AutoVideo Studio
cd /d "%~dp0"
if not exist .venv\Scripts\activate.bat (
  echo Rode primeiro o INSTALAR.bat
  pause
  exit /b
)
call .venv\Scripts\activate.bat
echo Abrindo o AutoVideo Studio no navegador... (nao feche esta janela enquanto usar)
python -m streamlit run app.py --server.headless false --browser.gatherUsageStats false
pause
