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
# conserta atalhos antigos/feitos à mão que apontam para o programa: coloca o logo neles também
foreach ($pasta in @([Environment]::GetFolderPath('Desktop'), [Environment]::GetFolderPath('CommonDesktopDirectory'))) {{
  Get-ChildItem -Path $pasta -Filter *.lnk -ErrorAction SilentlyContinue | ForEach-Object {{
    try {{
      $l = $s.CreateShortcut($_.FullName)
      if (($l.TargetPath + ' ' + $l.Arguments) -match 'AutoVideoStudio') {{
        $l.IconLocation = '{ps(icone)},0'
        $l.Save()
      }}
    }} catch {{}}
  }}
}}
# faz o Windows mostrar o ícone novo na hora
try {{ Start-Process -FilePath 'ie4uinit.exe' -ArgumentList '-show' -WindowStyle Hidden }} catch {{}}
"""
r = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
                   capture_output=True, text=True, creationflags=0x08000000 if sys.platform == "win32" else 0)
if r.returncode == 0:
    marca = APP / "dados" / "atalhos_v2.ok"
    marca.parent.mkdir(parents=True, exist_ok=True)
    marca.write_text("ok", encoding="utf-8")
print("Atalhos criados na Área de Trabalho e no menu Iniciar." if r.returncode == 0 else f"Não criei os atalhos: {r.stderr[:300]}")
