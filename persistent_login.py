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
from webdriver_manager.chrome import ChromeDriverManager
from colorama import Fore, Style, init

# ===== CONFIGURAÇÃO =====
URL_BIGCLIENT = "https://habblive.in/bigclient/"
CHECK_INTERVAL = 15  # segundos entre verificações
EXECUTAR_ACOES = True  # True = faz ações no quarto, False = só loga/reloga

# Configurações personalizadas
DONO_QUARTO = "Solitudine"  # Nome do dono a ser digitado no filtro
NOME_QUARTO = "Meu Quarto Teste"  # Nome exato do quarto a ser clicado
# ========================

init(autoreset=True)

status_contas = {}
lock = threading.Lock()

def log(msg, color=Fore.WHITE):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"{color}[{timestamp}] {msg}{Style.RESET_ALL}")

def painel_status(total_contas):
    while True:
        with lock:
            status_parts = []
            for i in range(1, total_contas + 1):
                estado = status_contas.get(i, "⏳ Iniciando")
                status_parts.append(f"[Conta {i}] {estado}")
            painel = " | ".join(status_parts)
        log(painel, Fore.BLUE)
        time.sleep(5)

def executar_acoes_no_quarto(driver, index):
    """Executa a sequência de ações dentro do cliente."""
    wait = WebDriverWait(driver, 20)
    try:
        # 1. Aguardar 15 segundos
        log(f"[Conta {index}] Aguardando 15s antes de iniciar ações...", Fore.YELLOW)
        time.sleep(15)

        # 2. Abrir o navegador de quartos
        nav_btn = wait.until(EC.element_to_be_clickable(
            (By.CSS_SELECTOR, ".cursor-pointer.navigation-item.icon.icon-rooms")
        ))
        nav_btn.click()
        log(f"[Conta {index}] Navegador de Quartos aberto.", Fore.GREEN)

        # 3. Aguardar 4 segundos
        time.sleep(4)

        # 4. Clicar no <select>
        select_elem = wait.until(EC.element_to_be_clickable(
            (By.CSS_SELECTOR, "select.form-select.form-select-sm")
        ))
        select_elem.click()
        log(f"[Conta {index}] Menu de filtro aberto.", Fore.GREEN)

        # 5. Aguardar 4 segundos
        time.sleep(4)

        # 6. Clicar na opção "Dono"
        option_elem = wait.until(EC.element_to_be_clickable(
            (By.CSS_SELECTOR, "select.form-select.form-select-sm option[value='2']")
        ))
        option_elem.click()
        log(f"[Conta {index}] Filtro 'Dono' selecionado.", Fore.GREEN)

        # 7. Aguardar 4 segundos
        time.sleep(4)

        # 8. Clicar no campo de filtro de texto
        filtro_input = wait.until(EC.element_to_be_clickable(
            (By.CSS_SELECTOR, "input.form-control.form-control-sm[placeholder='filtrar quartos por']")
        ))
        filtro_input.click()
        log(f"[Conta {index}] Campo de filtro selecionado.", Fore.GREEN)

        # 9. Aguardar 4 segundos
        time.sleep(4)

        # 10. Escrever nome do dono
        filtro_input.send_keys(DONO_QUARTO)
        log(f"[Conta {index}] Texto '{DONO_QUARTO}' digitado.", Fore.MAGENTA)

        # 11. Aguardar 4 segundos
        time.sleep(4)

        # 12. Clicar no botão de busca
        btn_buscar = wait.until(EC.element_to_be_clickable(
            (By.CSS_SELECTOR, ".d-flex.align-items-center.justify-content-center.btn.btn-primary.btn-sm")
        ))
        btn_buscar.click()
        log(f"[Conta {index}] Botão de busca clicado.", Fore.GREEN)

        # 13. Aguardar 15 segundos
        time.sleep(15)

        # 14. Clicar no quarto pelo nome
        quarto_elem = wait.until(EC.element_to_be_clickable(
            (By.XPATH, f"//div[@class='flex-grow-1 d-inline text-black text-truncate' and normalize-space(text())='{NOME_QUARTO}']")
        ))
        quarto_elem.click()
        log(f"[Conta {index}] Entrando no quarto '{NOME_QUARTO}'...", Fore.GREEN)

    except Exception as e:
        log(f"[Conta {index}] Erro ao executar ações no quarto: {e}", Fore.RED)

def iniciar_sessao(username, password, index):
    time.sleep(index * 3)  # delay inicial para evitar logins simultâneos

    while True:
        with lock:
            status_contas[index] = "🔄 Relogando"

        options = Options()
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--incognito")

        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)

        try:
            log(f"[Conta {index}] Iniciando login para {username}...", Fore.CYAN)
            driver.get("https://habblive.in/")
            wait = WebDriverWait(driver, 20)

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

            # Preenche login
            wait.until(EC.presence_of_element_located((By.NAME, "username"))).send_keys(username)
            wait.until(EC.presence_of_element_located((By.NAME, "password"))).send_keys(password)

            # Aguarda botão visível e clicável
            login_button = wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, ".btn.big.green.login-button"))
            )
            login_button.click()

            time.sleep(5)
            driver.get(URL_BIGCLIENT)
            log(f"[Conta {index}] ✅ Online no Big Client.", Fore.GREEN)

            with lock:
                status_contas[index] = "✅ Online"

            # Executa ações no quarto se ativado
            if EXECUTAR_ACOES:
                executar_acoes_no_quarto(driver, index)

            # Loop de verificação
            while True:
                current_url = driver.current_url

                # Se saiu do Big Client, reloga
                if current_url != URL_BIGCLIENT:
                    log(f"[Conta {index}] ⚠️ Redirecionado para fora ({current_url}). Relogando...", Fore.YELLOW)
                    driver.quit()
                    time.sleep(2)
                    break

                # Detecta reinício do cliente (mesma URL mas elementos sumiram)
                try:
                    driver.find_element(By.CSS_SELECTOR, ".cursor-pointer.navigation-item.icon.icon-rooms")
                except:
                    log(f"[Conta {index}] ⚠️ Cliente reiniciou, aguardando recarregar...", Fore.YELLOW)
                    try:
                        WebDriverWait(driver, 60).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, ".cursor-pointer.navigation-item.icon.icon-rooms"))
                        )
                        log(f"[Conta {index}] Cliente recarregado.", Fore.GREEN)
                        if EXECUTAR_ACOES:
                            executar_acoes_no_quarto(driver, index)
                    except:
                        log(f"[Conta {index}] ❌ Cliente não recarregou a tempo.", Fore.RED)

                time.sleep(CHECK_INTERVAL)

        except Exception as e:
            log(f"[Conta {index}] ❌ Erro: {e}", Fore.RED)
            with lock:
                status_contas[index] = "❌ Erro"
            driver.quit()
            time.sleep(5)

# Lê todas as contas, mesmo com buracos
accounts = []
i = 1
while i <= 100:
    user = os.getenv(f"HABBLIVE_USERNAME_{i}")
    pwd = os.getenv(f"HABBLIVE_PASSWORD_{i}")
    if user and pwd:
        accounts.append((user, pwd))
    i += 1

if not accounts:
    raise ValueError("Nenhuma conta configurada nos secrets.")

# Inicializa status
with lock:
    for idx in range(1, len(accounts) + 1):
        status_contas[idx] = "⏳ Iniciando"

# Thread do painel
painel_thread = threading.Thread(target=painel_status, args=(len(accounts),))
painel_thread.start()

# Threads das contas
threads = []
for idx, (username, password) in enumerate(accounts, start=1):
    t = threading.Thread(target=iniciar_sessao, args=(username, password, idx))
    t.start()
    threads.append(t)

# Mantém todas as threads vivas
for t in threads:
    t.join()

painel_thread.join()
