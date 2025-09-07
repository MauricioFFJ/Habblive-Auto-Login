import os
import time
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from colorama import Fore, Style, init

# ===== CONFIGURAÇÃO =====
TEMPO_ONLINE = 20  # segundos que cada conta ficará no Big Client
MAX_TENTATIVAS = 3  # número de tentativas de login por conta
# ========================

init(autoreset=True)

def log(msg, color=Fore.WHITE):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"{color}[{timestamp}] {msg}{Style.RESET_ALL}")

def tentar_login(driver, username, password, index):
    """Executa o processo de login. Retorna True se sucesso, False se falhar."""
    wait = WebDriverWait(driver, 15)

    # Fecha banner de cookies se aparecer
    try:
        cookie_banner = wait.until(
            EC.presence_of_element_located((By.ID, "cookie-law-container"))
        )
        try:
            accept_btn = cookie_banner.find_element(By.TAG_NAME, "button")
            accept_btn.click()
            log(f"[Conta {index}] Banner de cookies fechado.", Fore.MAGENTA)
        except:
            driver.execute_script("""
                var el = document.getElementById('cookie-law-container');
                if (el) el.remove();
            """)
            log(f"[Conta {index}] Banner de cookies removido via script.", Fore.MAGENTA)
    except:
        pass

    # Usuário
    try:
        user_input = wait.until(
            EC.presence_of_element_located((By.NAME, "username"))
        )
        user_input.clear()
        user_input.send_keys(username)
    except:
        log(f"[Conta {index}] ❌ Campo de usuário não encontrado", Fore.RED)
        return False

    # Senha
    try:
        pass_input = wait.until(
            EC.presence_of_element_located((By.NAME, "password"))
        )
        pass_input.clear()
        pass_input.send_keys(password)
    except:
        log(f"[Conta {index}] ❌ Campo de senha não encontrado", Fore.RED)
        return False

    # Botão de login
    try:
        login_button = wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, ".btn.big.green.login-button"))
        )
        login_button.click()
    except:
        log(f"[Conta {index}] ❌ Botão de login não encontrado ou não clicável", Fore.RED)
        return False

    time.sleep(5)  # aguarda login
    return True

def login_and_stay(username, password, index):
    for tentativa in range(1, MAX_TENTATIVAS + 1):
        options = Options()
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")

        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)

        try:
            log(f"[Conta {index}] Tentativa {tentativa} de login para {username}...", Fore.CYAN)
            driver.get("https://habblive.in/")

            if tentar_login(driver, username, password, index):
                log(f"[Conta {index}] Login concluído. Acessando Big Client...", Fore.GREEN)
                driver.get("https://habblive.in/bigclient/")

                log(f"[Conta {index}] Online no Big Client. Mantendo por {TEMPO_ONLINE} segundos...", Fore.YELLOW)
                for remaining in range(TEMPO_ONLINE, 0, -1):
                    log(f"[Conta {index}] {remaining}s restantes", Fore.BLUE)
                    time.sleep(1)

                log(f"[Conta {index}] ✅ Sessão finalizada.", Fore.MAGENTA)
                driver.quit()
                return True
            else:
                log(f"[Conta {index}] Falha na tentativa {tentativa}.", Fore.RED)

        except Exception as e:
            log(f"[Conta {index}] ❌ Erro: {e}", Fore.RED)
        finally:
            driver.quit()

    log(f"[Conta {index}] ❌ Todas as tentativas de login falharam", Fore.RED)
    return False

# Lê contas dos secrets
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

# Processa cada conta em sequência
sucesso = 0
erro = 0
for idx, (username, password) in enumerate(accounts, start=1):
    if login_and_stay(username, password, idx):
        sucesso += 1
    else:
        erro += 1

# Resumo final
log(f"Resumo final: {sucesso} contas concluíram com sucesso, {erro} contas tiveram erro.", Fore.CYAN)
