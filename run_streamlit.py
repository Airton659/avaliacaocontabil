# run_streamlit.py
import os, sys, socket, webbrowser
import streamlit.web.cli as stcli

def _app_path():
    bundle_dir = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(bundle_dir, "app.py")

def _pick_free_port(preferred=8501):
    # tenta a 8501; se ocupada, pede uma porta livre ao SO
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("0.0.0.0", preferred))
            return preferred
    except OSError:
        pass
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("0.0.0.0", 0))
        return s.getsockname()[1]

def _lan_ip():
    # descobre o IP da rede local sem fazer requisição externa
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))  # não envia dados; só resolve rota
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        try:
            return socket.gethostbyname(socket.gethostname())
        except Exception:
            return "127.0.0.1"

if __name__ == "__main__":
    app = _app_path()
    port = _pick_free_port()
    lan = _lan_ip()

    # Streamlit ouvindo em todas as interfaces
    sys.argv = [
        "streamlit", "run", app,
        "--server.headless=true",
        "--global.developmentMode=false",
        "--browser.gatherUsageStats=false",
        "--server.address=0.0.0.0",
        f"--server.port={port}",
        "--server.enableCORS=false",             # facilita acesso via LAN
        "--server.enableXsrfProtection=false"    # idem (use apenas em rede confiável)
    ]

    local_url = f"http://127.0.0.1:{port}"
    lan_url   = f"http://{lan}:{port}"

    # abre o navegador local e imprime as URLs claras no console
    try:
        webbrowser.open(local_url, new=1, autoraise=True)
    except Exception:
        pass

    print("\nVocê pode acessar o painel pelos endereços:")
    print(f"  Localhost: {local_url}")
    print(f"  Rede local (LAN): {lan_url}\n")
    print("Obs.: se não abrir pela LAN, confira o firewall do Windows e da sua rede.\n")

    stcli.main()
