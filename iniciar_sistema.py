
import threading
import time
import webbrowser
from urllib.request import urlopen

from app import app


HOST = "127.0.0.1"
PORTA = 5000
URL = f"http://{HOST}:{PORTA}"


def abrir_navegador():
    for _ in range(40):
        try:
            with urlopen(URL, timeout=1) as resposta:
                if resposta.status == 200:
                    webbrowser.open(URL)
                    return
        except Exception:
            time.sleep(0.5)

    print("Não foi possível abrir o navegador automaticamente.")
    print(f"Acesse manualmente: {URL}")


def iniciar():
    navegador = threading.Thread(
        target=abrir_navegador,
        daemon=True
    )

    navegador.start()

    print("Sistema de Controle de Atipicidades")
    print(f"Acesse: {URL}")

    app.run(
        host=HOST,
        port=PORTA,
        debug=False,
        use_reloader=False
    )


if __name__ == "__main__":
    iniciar()
