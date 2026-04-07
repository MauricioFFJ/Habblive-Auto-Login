import os
import time
import threading
from datetime import datetime

from playwright.sync_api import sync_playwright
from colorama import Fore, Style, init

init(autoreset=True)

URL = "https://habblive.in/"

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


def encontrar_input(page, seletores):

    for s in seletores:
        try:
            if page.locator(s).count() > 0:
                return s
        except:
            pass

    return None


def iniciar_conta(username, password, index):

    time.sleep(index * 5)

    while True:

        with lock:
            status_contas[index] = "🔄"

        try:

            with sync_playwright() as p:

                browser = p.chromium.launch(
                    headless=True,
                    args=[
                        "--no-sandbox",
                        "--disable-dev-shm-usage"
                    ]
                )

                context = browser.new_context()
                page = context.new_page()

                log(f"[Conta {index}] Abrindo site...", Fore.CYAN)

                page.goto(URL, timeout=120000)

                page.wait_for_timeout(5000)

                log(f"[Conta {index}] Detectando campos de login...", Fore.YELLOW)

                user_selector = encontrar_input(page, [
                    'input[name="username"]',
                    'input[name="login"]',
                    'input[name="email"]',
                    'input[id="username"]',
                    'input[type="text"]'
                ])

                pass_selector = encontrar_input(page, [
                    'input[name="password"]',
                    'input[id="password"]',
                    'input[type="password"]'
                ])

                if not user_selector or not pass_selector:
                    raise Exception("Campos de login não encontrados")

                page.fill(user_selector, username)
                page.fill(pass_selector, password)

                log(f"[Conta {index}] Enviando login...", Fore.YELLOW)

                btn = page.locator("button, input[type=submit]").first
                btn.click()

                page.wait_for_timeout(8000)

                if "login" in page.url.lower():
                    raise Exception("Login não confirmado")

                log(f"[Conta {index}] Login confirmado!", Fore.GREEN)

                with lock:
                    status_contas[index] = "✅"

                while True:

                    page.wait_for_timeout(CHECK_INTERVAL * 1000)

                    if page.is_closed():
                        raise Exception("Página fechada")

                    log(f"[Conta {index}] Sessão ativa.", Fore.GREEN)

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
