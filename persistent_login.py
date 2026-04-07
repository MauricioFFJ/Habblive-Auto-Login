import os
import time
import threading
from datetime import datetime

import requests
from bs4 import BeautifulSoup
from colorama import Fore, Style, init

init(autoreset=True)

URL_HOME = "https://habblive.in/"
URL_LOGIN = "https://habblive.in/login"
URL_CLIENT = "https://habblive.in/bigclient/"

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

    s = requests.Session()

    s.headers.update({
        "User-Agent":
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Accept":
        "text/html,application/xhtml+xml",
        "Connection":
        "keep-alive"
    })

    return s


def obter_csrf(session):

    r = session.get(URL_LOGIN, timeout=30)

    soup = BeautifulSoup(r.text, "html.parser")

    token = soup.find("input", {"name": "_token"})

    if not token:
        raise Exception("CSRF token não encontrado")

    return token["value"]


def fazer_login(session, username, password, index):

    log(f"[Conta {index}] Preparando login...", Fore.CYAN)

    csrf = obter_csrf(session)

    payload = {
        "_token": csrf,
        "username": username,
        "password": password
    }

    log(f"[Conta {index}] Enviando login...", Fore.YELLOW)

    r = session.post(URL_LOGIN, data=payload, timeout=30)

    if "logout" not in r.text.lower():
        raise Exception("Login rejeitado")

    log(f"[Conta {index}] Login confirmado!", Fore.GREEN)


def manter_sessao(session, index):

    while True:

        try:

            r = session.get(URL_CLIENT, timeout=30)

            if r.status_code != 200:
                raise Exception("Sessão inválida")

            log(f"[Conta {index}] Sessão ativa.", Fore.GREEN)

        except:

            log(f"[Conta {index}] Sessão perdida.", Fore.RED)

            return

        time.sleep(CHECK_INTERVAL)


def iniciar_conta(username, password, index):

    time.sleep(index * 3)

    while True:

        with lock:
            status_contas[index] = "🔄"

        try:

            session = criar_sessao()

            fazer_login(session, username, password, index)

            with lock:
                status_contas[index] = "✅"

            manter_sessao(session, index)

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
