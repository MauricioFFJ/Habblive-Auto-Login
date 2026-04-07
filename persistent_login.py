import os
import time
import threading
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from colorama import Fore, Style, init


URL_HOME = "https://habblive.in/"
URL_BIGCLIENT = "https://habblive.in/bigclient/"

CHECK_INTERVAL = 15

init(autoreset=True)

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


def criar_driver():

    options = Options()

    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    options.add_argument("--disable-blink-features=AutomationControlled")

    options.add_argument("--disable-gpu")

    options.add_argument("--window-size=1366,768")

    options.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    )

    service = Service()

    driver = webdriver.Chrome(service=service, options=options)

    driver.execute_script(
        "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    )

    driver.set_page_load_timeout(120)

    return driver


def fazer_login(driver, username, password, index):

    log(f"[Conta {index}] Abrindo site...", Fore.CYAN)

    driver.get(URL_HOME)

    wait = WebDriverWait(driver, 120)

    user = wait.until(
        EC.presence_of_element_located((By.NAME, "username"))
    )

    pwd = wait.until(
        EC.presence_of_element_located((By.NAME, "password"))
    )

    user.clear()
    pwd.clear()

    user.send_keys(username)
    pwd.send_keys(password)

    btn = wait.until(
        EC.element_to_be_clickable(
            (By.CSS_SELECTOR, ".btn.big.green.login-button")
        )
    )

    driver.execute_script("arguments[0].click();", btn)

    time.sleep(5)

    driver.get(URL_BIGCLIENT)

    log(f"[Conta {index}] Login concluído.", Fore.GREEN)


def monitorar_client(driver, index):

    while True:

        try:

            driver.find_element(
                By.CSS_SELECTOR,
                ".cursor-pointer.navigation-item.icon.icon-rooms"
            )

        except:

            log(f"[Conta {index}] Cliente reiniciando...", Fore.YELLOW)

            try:

                WebDriverWait(driver, 90).until(

                    EC.presence_of_element_located(
                        (
                            By.CSS_SELECTOR,
                            ".cursor-pointer.navigation-item.icon.icon-rooms"
                        )
                    )
                )

                log(f"[Conta {index}] Cliente voltou.", Fore.GREEN)

            except:

                log(f"[Conta {index}] Cliente não voltou.", Fore.RED)

                return

        time.sleep(CHECK_INTERVAL)


def iniciar_conta(username, password, index):

    time.sleep(index * 3)

    while True:

        with lock:
            status_contas[index] = "🔄"

        driver = None

        try:

            driver = criar_driver()

            fazer_login(driver, username, password, index)

            with lock:
                status_contas[index] = "✅"

            monitorar_client(driver, index)

        except Exception as e:

            log(f"[Conta {index}] ERRO: {repr(e)}", Fore.RED)

            with lock:
                status_contas[index] = "❌"

        finally:

            if driver:

                try:
                    driver.quit()
                except:
                    pass

        log(f"[Conta {index}] Relogando em 5s...", Fore.YELLOW)

        time.sleep(5)


accounts = []

for i in range(1, 101):

    user = os.getenv(f"HABBLIVE_USERNAME_{i}")
    pwd = os.getenv(f"HABBLIVE_PASSWORD_{i}")

    if user and pwd:
        accounts.append((user, pwd))


if not accounts:
    raise ValueError("Nenhuma conta encontrada.")


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
