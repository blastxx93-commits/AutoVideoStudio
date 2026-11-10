"""Cria os atalhos 'AutoVideo Studio' na Área de Trabalho e no menu Iniciar (rodado pelo INSTALAR.bat)."""
import subprocess
import sys
from pathlib import Path

APP = Path(__file__).resolve().parent
pyw = APP / ".venv" / "Scripts" / "pythonw.exe"
if not pyw.exists():
    pyw = Path(sys.executable).with_name("pythonw.exe")
alvo, launcher, icone = str(pyw), str(APP / "AutoVideoStudio.pyw"), str(APP / "assets" / "icone.ico")


def ps(texto):
    return texto.replace("'", "''")


script = f"""
$s = New-Object -ComObject WScript.Shell
foreach ($pasta in @([Environment]::GetFolderPath('Desktop'), [Environment]::GetFolderPath('Programs'))) {{
  $l = $s.CreateShortcut((Join-Path $pasta 'AutoVideo Studio.lnk'))
  $l.TargetPath = '{ps(alvo)}'
  $l.Arguments = '"{ps(launcher)}"'
  $l.WorkingDirectory = '{ps(str(APP))}'
  $l.IconLocation = '{ps(icone)},0'
  $l.Description = 'AutoVideo Studio'
  $l.Save()
}}
"""
r = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
                   capture_output=True, text=True)
print("Atalhos criados na Área de Trabalho e no menu Iniciar." if r.returncode == 0 else f"Não criei os atalhos: {r.stderr[:300]}")
