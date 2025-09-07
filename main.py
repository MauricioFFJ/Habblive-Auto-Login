import os
import time
import threading
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from colorama import Fore, Style, init

# Inicializa cores no terminal
init(autoreset=True)

# Variável global para armazenar tempo restante de cada conta
tempo_restante = {}
lock = threading.Lock()

def log(msg, color=Fore.WHITE):
    """Imprime mensagem com timestamp e cor."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"{color}[{timestamp}] {msg}{Style.RESET_ALL}")

def painel_contador(total_contas):
    """Mostra o contador sincronizado e para quando todas concluírem."""
    while True:
        with lock:
            status_parts = []
            concluidas = 0
            for i in range(1, total_contas+1):
                if tempo_restante.get(i) == "done":
                    status_parts.append(f"[Conta {i}] ✅ Concluído")
                    concluidas += 1
                else:
                    status_parts.append(f"[Conta {i}] {tempo_restante.get(i, 0)}s restantes")
            status = " | ".join(status_parts)

        log(status, Fore.BLUE)

        if concluidas == total_contas:
            break
        time.sleep(1)

def login_and_stay(username, password, index):
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    # CORREÇÃO: usar Service para evitar conflito de argumentos
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

    try:
        log(f"[Conta {index}] Iniciando login para {username}...", Fore.CYAN)
        driver.get("https://habblive.in/")

        driver.find_element(By.NAME, "username").send_keys(username)
        driver.find_element(By.NAME, "password").send_keys(password)
        driver.find_element(By.XPATH, "//button[@type='submit']").click()

        time.sleep(5)  # aguarda login

        log(f"[Conta {index}] Login concluído. Acessando Big Client...", Fore.GREEN)
        driver.get("https://habblive.in/bigclient/")

        log(f"[Conta {index}] Online no Big Client. Mantendo por 3 minutos...", Fore.YELLOW)

        # Contagem regressiva
        for remaining in range(180, 0, -1):
            with lock:
                tempo_restante[index] = remaining
            time.sleep(1)

        log(f"[Conta {index}] Sessão finalizada.", Fore.MAGENTA)
        with lock:
            tempo_restante[index] = "done"

    except Exception as e:
        log(f"[Conta {index}] Erro: {e}", Fore.RED)
        with lock:
            tempo_restante[index] = "done"
    finally:
        driver.quit()

# Lê todas as contas dos secrets
accounts = []
i = 1
while True:
    user = os.getenv(f"HABBLIVE_USERNAME_{i}")
    pwd = os.getenv(f"HABBLIVE_PASSWORD_{i}")
    if not user or not pwd:
        break
    accounts.append((user, pwd))
    i += 1

if not accounts:
    raise ValueError("Nenhuma conta configurada nos secrets.")

# Inicializa tempo_restante
with lock:
    for idx in range(1, len(accounts)+1):
        tempo_restante[idx] = 180

# Thread do painel
painel_thread = threading.Thread(target=painel_contador, args=(len(accounts),))
painel_thread.start()

# Threads de login
threads = []
for idx, (username, password) in enumerate(accounts, start=1):
    t = threading.Thread(target=login_and_stay, args=(username, password, idx))
    t.start()
    threads.append(t)

# Aguarda todas as threads terminarem
for t in threads:
    t.join()

# Aguarda painel encerrar
painel_thread.join()
