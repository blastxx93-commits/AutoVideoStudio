"""AutoVideo Studio — abre o programa numa janela própria, sem navegador e sem a janela preta (CMD).
É iniciado pelo atalho da Área de Trabalho / menu Iniciar (criado pelo INSTALAR.bat)."""
import base64
import os
import socket
import subprocess
import sys
import threading
import time
import urllib.request
from pathlib import Path

APP = Path(__file__).resolve().parent
LOG = APP / "dados" / "programa_log.txt"
FLAG = APP / "dados" / "reiniciar.flag"   # criado pelo atualizador: "reinicie o programa"
PORTA_PADRAO = 8501
TITULO = "AutoVideo Studio"
NO_WINDOW = 0x08000000 if os.name == "nt" else 0


def porta_livre(p):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("127.0.0.1", p)) != 0


def servidor_ok(porta):
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{porta}/_stcore/health", timeout=1) as r:
            return r.status == 200
    except Exception:
        return False


def iniciar_servidor(com_janela=True):
    """Sobe o servidor do programa escondido. Se já estiver aberto, reaproveita (uma janela só)."""
    if servidor_ok(PORTA_PADRAO):
        return PORTA_PADRAO, None
    porta = PORTA_PADRAO
    while not porta_livre(porta):
        porta += 1
    LOG.parent.mkdir(parents=True, exist_ok=True)
    py = Path(sys.executable)
    if py.name.lower() == "pythonw.exe" and (py.parent / "python.exe").exists():
        py = py.parent / "python.exe"  # roda escondido mesmo assim (CREATE_NO_WINDOW)
    env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1", AVS_LAUNCHER="1" if com_janela else "0")
    proc = subprocess.Popen(
        [str(py), "-m", "streamlit", "run", str(APP / "app.py"), "--server.headless", "true",
         "--server.port", str(porta), "--server.address", "127.0.0.1", "--browser.gatherUsageStats", "false",
         "--client.toolbarMode", "minimal"],
        cwd=str(APP), stdout=open(LOG, "a", encoding="utf-8"), stderr=subprocess.STDOUT,
        creationflags=NO_WINDOW, env=env)
    return porta, proc


def splash_html(texto="Abrindo o estúdio…"):
    logo = APP / "assets" / "logo_escuro.png"
    b64 = base64.b64encode(logo.read_bytes()).decode() if logo.exists() else ""
    return f"""<html><body style="margin:0;background:radial-gradient(1200px 600px at 80% -10%,#16306e,#070F24 60%);
height:100vh;display:flex;flex-direction:column;align-items:center;justify-content:center;font-family:Segoe UI,Arial;color:#EAF0FF">
<img src="data:image/png;base64,{b64}" style="width:420px;filter:drop-shadow(0 10px 30px rgba(47,123,255,.5))">
<div style="margin-top:34px;width:260px;height:6px;border-radius:6px;background:#1E3270;overflow:hidden">
<div style="width:40%;height:6px;border-radius:6px;background:linear-gradient(90deg,#1D4ED8,#38BDF8);
animation:c 1.1s ease-in-out infinite"></div></div>
<p style="margin-top:16px;color:#8FA3D1;font-size:14px">{texto}</p>
<style>@keyframes c{{0%{{transform:translateX(-110%)}}100%{{transform:translateX(260%)}}}}</style></body></html>"""


def esperar(porta, segundos=90):
    t0 = time.time()
    while time.time() - t0 < segundos:
        if servidor_ok(porta):
            return True
        time.sleep(0.4)
    return False


def main():
    try:
        import webview  # noqa
        tem_janela = True
    except ImportError:
        tem_janela = False
    FLAG.unlink(missing_ok=True)
    porta, proc = iniciar_servidor(tem_janela)
    url = f"http://127.0.0.1:{porta}"
    try:
        import webview  # pywebview: janela nativa do Windows (Edge WebView2)
    except ImportError:
        webview = None

    if webview is None:  # plano B: Edge em "modo aplicativo" (janela sem barra de endereço)
        esperar(porta)
        edge = [r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
                r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"]
        exe = next((e for e in edge if os.path.exists(e)), None)
        if exe:
            subprocess.Popen([exe, f"--app={url}", "--window-size=1440,920"], creationflags=NO_WINDOW)
        else:
            import webbrowser
            webbrowser.open(url)
        return  # o servidor continua; use o botão "Sair do programa" dentro do app para fechar

    janela = webview.create_window(TITULO, html=splash_html(), width=1440, height=920, min_size=(1100, 700),
                                   background_color="#070F24", text_select=True)

    def carregar():
        if esperar(porta):
            janela.load_url(url)
        else:
            janela.load_html("<body style='background:#070F24;color:#fff;font-family:Segoe UI;padding:40px'>"
                             "<h2>Não consegui abrir o programa.</h2><p>Veja o arquivo dados/programa_log.txt "
                             "ou rode o ABRIR.bat para ver o erro.</p></body>")

    atual = {"porta": porta, "proc": proc}

    def vigiar():
        """Depois de uma atualização o programa se fecha e deixa o FLAG: reabre na mesma janela."""
        while True:
            time.sleep(1)
            if not FLAG.exists() or servidor_ok(atual["porta"]):
                continue
            try:
                FLAG.unlink(missing_ok=True)
                janela.load_html(splash_html("Atualização instalada. Reabrindo o estúdio…"))
                if atual["proc"]:
                    try:
                        atual["proc"].wait(timeout=10)
                    except Exception:
                        pass
                time.sleep(1)
                atual["porta"], atual["proc"] = iniciar_servidor(True)
                if esperar(atual["porta"]):
                    janela.load_url(f"http://127.0.0.1:{atual['porta']}")
            except Exception:
                pass

    threading.Thread(target=carregar, daemon=True).start()
    threading.Thread(target=vigiar, daemon=True).start()
    webview.start(private_mode=False, storage_path=str(APP / "dados" / "janela"))
    # janela fechada: desliga o servidor (vídeos em geração continuam até terminar)
    if atual["proc"]:
        atual["proc"].terminate()


if __name__ == "__main__":
    main()
