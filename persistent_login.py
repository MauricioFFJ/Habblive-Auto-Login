import os
import time
import threading
from datetime import datetime

import requests
from colorama import Fore, Style, init

init(autoreset=True)

LOGIN_URL = "https://habblive.in/api/login"
CLIENT_URL = "https://habblive.in/bigclient/"
PING_URL = "https://habblive.in/api/me"

CHECK_INTERVAL = 30

status_contas = {}
lock = threading.Lock()


def log(msg, color=Fore.WHITE):
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"{color}[{timestamp}] {msg}{Style.RESET_ALL}")


def painel_status(total):

    while True:

        with lock:

            linha = []

            for i in range(1, total + 1):
                estado = status_contas.get(i, "⏳")
                linha.append(f"[{i}:{estado}]")

            log(" ".join(linha), Fore.BLUE)

        time.sleep(5)


def criar_sessao():

    session = requests.Session()

    session.headers.update({

        "User-Agent":
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",

        "Accept":
        "application/json, text/plain, */*",

        "Content-Type":
        "application/json"

    })

    return session


def fazer_login(session, username, password, index):

    log(f"[Conta {index}] Enviando login...", Fore.YELLOW)

    payload = {

        "username": username,
        "password": password

    }

    r = session.post(LOGIN_URL, json=payload, timeout=30)

    if r.status_code != 200:
        raise Exception("Falha HTTP login")

    data = r.json()

    if not data.get("success"):
        raise Exception("Login rejeitado")

    log(f"[Conta {index}] Login confirmado!", Fore.GREEN)


def verificar_sessao(session):

    try:

        r = session.get(PING_URL, timeout=20)

        return r.status_code == 200

    except:
        return False


def manter_cliente(session, index):

    while True:

        ok = verificar_sessao(session)

        if not ok:

            log(f"[Conta {index}] Sessão perdida.", Fore.RED)

            return

        log(f"[Conta {index}] Sessão ativa.", Fore.GREEN)

        time.sleep(CHECK_INTERVAL)


def iniciar_conta(username, password, index):

    time.sleep(index * 3)

    while True:

        with lock:
            status_contas[index] = "🔄"

        session = None

        try:

            session = criar_sessao()

            fazer_login(session, username, password, index)

            with lock:
                status_contas[index] = "✅"

            manter_cliente(session, index)

        except Exception as e:

            log(f"[Conta {index}] ERRO: {repr(e)}", Fore.RED)

            with lock:
                status_contas[index] = "❌"

        log(f"[Conta {index}] Relogando em 20s...", Fore.YELLOW)

        time.sleep(20)


accounts = []

for i in range(1, 101):

    user = os.getenv(f"HABBLIVE_USERNAME_{i}")
    pwd = os.getenv(f"HABBLIVE_PASSWORD_{i}")

    if user and pwd:
        accounts.append((user, pwd))


if not accounts:
    raise Exception("Nenhuma conta configurada")


with lock:

    for i in range(1, len(accounts) + 1):
        status_contas[i] = "⏳"


painel = threading.Thread(
    target=painel_status,
    args=(len(accounts),),
    daemon=True
)

painel.start()


threads = []

for idx, (username, password) in enumerate(accounts, start=1):

    t = threading.Thread(
        target=iniciar_conta,
        args=(username, password, idx)
    )

    t.start()

    threads.append(t)


for t in threads:
    t.join()
