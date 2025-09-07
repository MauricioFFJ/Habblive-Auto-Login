import os
import time
import threading
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
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
DONO_QUARTO = "Solitudine"         # Nome do dono a ser digitado no filtro
NOME_QUARTO = "Bar Taberna (+18)"   # Nome exato (ou parte) do quarto a ser clicado
MENSAGEM_CHAT = "2288"             # Mensagem a ser digitada no chat após entrar

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

# ---------- Helpers robustos ----------
def wait_click_css(driver, css, desc, timeout=30, use_js=False):
    wait = WebDriverWait(driver, timeout)
    elem = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, css)))
    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", elem)
    time.sleep(0.2)
    if use_js:
        driver.execute_script("arguments[0].click();", elem)
    else:
        try:
            elem.click()
        except Exception:
            driver.execute_script("arguments[0].click();", elem)
    log(f"{desc} clicado.", Fore.GREEN)
    return elem

def wait_click_xpath(driver, xpath, desc, timeout=40, use_js=False):
    wait = WebDriverWait(driver, timeout)
    elem = wait.until(EC.element_to_be_clickable((By.XPATH, xpath)))
    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", elem)
    time.sleep(0.2)
    if use_js:
        driver.execute_script("arguments[0].click();", elem)
    else:
        try:
            elem.click()
        except Exception:
            driver.execute_script("arguments[0].click();", elem)
    log(f"{desc} clicado.", Fore.GREEN)
    return elem

def wait_type_css(driver, css, text, desc, timeout=30, clear_first=False, fire_input=True):
    wait = WebDriverWait(driver, timeout)
    elem = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, css)))
    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", elem)
    time.sleep(0.2)
    elem.click()
    if clear_first:
        try:
            elem.clear()
        except Exception:
            pass
    elem.send_keys(text)
    if fire_input:
        try:
            driver.execute_script("arguments[0].dispatchEvent(new Event('input', {bubbles:true}));", elem)
            driver.execute_script("arguments[0].dispatchEvent(new Event('change', {bubbles:true}));", elem)
        except Exception:
            pass
    log(f"{desc} digitado: '{text}'.", Fore.MAGENTA)
    return elem

def selecionar_opcao_dono(driver):
    select_css = "select.form-select.form-select-sm"
    wait = WebDriverWait(driver, 30)
    select_elem = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, select_css)))
    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", select_elem)
    time.sleep(0.2)
    driver.execute_script("""
        arguments[0].value = '2';
        arguments[0].dispatchEvent(new Event('change', { bubbles: true }));
    """, select_elem)
    log("Filtro 'Dono' selecionado (via change event).", Fore.GREEN)
    return select_elem

def clicar_quarto_por_nome(driver, nome, timeout=40):
    mapa_maius = "ABCDEFGHIJKLMNOPQRSTUVWXYZÁÉÍÓÚÂÊÎÔÛÃÕÇ"
    mapa_minus = "abcdefghijklmnopqrstuvwxyzáéíóúâêîôûãõç"
    nome_lower = nome.lower()
    xpath_exato = (
        f"//div[@class='flex-grow-1 d-inline text-black text-truncate' and "
        f"translate(normalize-space(text()), '{mapa_maius}', '{mapa_minus}')='{nome_lower}']"
    )
    xpath_contains = (
        f"//div[@class='flex-grow-1 d-inline text-black text-truncate' and "
        f"contains(translate(normalize-space(text()), '{mapa_maius}', '{mapa_minus}'), '{nome_lower}')]"
    )
    try:
        return wait_click_xpath(driver, xpath_exato, f"Quarto '{nome}' (exato)", timeout=timeout, use_js=True)
    except Exception as e1:
        log(f"Quarto exato não encontrado: {repr(e1)}. Tentando por 'contém'...", Fore.YELLOW)
        return wait_click_xpath(driver, xpath_contains, f"Quarto contendo '{nome}'", timeout=timeout, use_js=True)

# Função auxiliar: realiza a ação extra no quarto
def acao_mensagem_quarto(driver, mensagem):
    try:
        time.sleep(5)
        input_chat = WebDriverWait(driver, 40).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "input.chat-input[placeholder='Fale aqui...']"))
        )
        input_chat.click()
        time.sleep(5)
        input_chat.send_keys(mensagem)
        log(f"Mensagem digitada: '{mensagem}'", Fore.MAGENTA)
        time.sleep(2)
        input_chat.send_keys(Keys.ENTER)
        log("ENTER pressionado no chat.", Fore.GREEN)
    except Exception as e:
        log(f"Erro ao digitar mensagem no chat: {repr(e)}", Fore.RED)

# ---------- Sequência de ações com retentativas ----------
def executar_acoes_no_quarto(driver, index):
    for tentativa in range(1, 4):
        try:
            log(f"[Conta {index}] Iniciando sequência (tentativa {tentativa}/3). Aguardando 15s...", Fore.YELLOW)
            time.sleep(15)
            wait_click_css(driver, ".cursor-pointer.navigation-item.icon.icon-rooms",
                           "[Navegador de Quartos]", timeout=30, use_js=True)
            time.sleep(4)
            wait_click_css(driver, "select.form-select.form-select-sm",
                           "[Menu de filtro]", timeout=30, use_js=True)
            time.sleep(4)
            selecionar_opcao_dono(driver)
            time.sleep(4)
            wait_type_css(driver,
                          "input.form-control.form-control-sm[placeholder='filtrar quartos por']",
                          DONO_QUARTO, "[Filtro de texto - dono]", timeout=30,
                          clear_first=True, fire_input=True)
            time.sleep(4)
            wait_click_css(driver,
                           ".d-flex.align-items-center.justify-content-center.btn.btn-primary.btn-sm",
                           "[Botão Buscar]", timeout=30, use_js=True)
            time.sleep(15)
            clicar_quarto_por_nome(driver, NOME_QUARTO, timeout=45)
            log(f"[Conta {index}] Entrando no quarto '{NOME_QUARTO}'.", Fore.GREEN)
            # === AÇÃO EXTRA: Digitar mensagem no chat ===
            acao_mensagem_quarto(driver, MENSAGEM_CHAT)
            # Sequência concluída
            return
        except Exception as e:
            log(f"[Conta {index}] Falha na sequência (tentativa {tentativa}/3): {repr(e)}", Fore.RED)
            if tentativa < 3:
                time.sleep(6)
                try:
                    wait_click_css(driver, ".cursor-pointer.navigation-item.icon.icon-rooms",
                                   "[Reabrir Navegador de Quartos]", timeout=15, use_js=True)
                except Exception as e2:
                    log(f"[Conta {index}] Não conseguiu reabrir navegador: {repr(e2)}", Fore.YELLOW)
            else:
                log(f"[Conta {index}] Sequência falhou após 3 tentativas. Vai seguir monitorando.", Fore.RED)

def iniciar_sessao(username, password, index):
    time.sleep(index * 3)
    while True:
        with lock:
            status_contas[index] = "🔄 Relogando"
        options = Options()
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--incognito")
        options.add_argument("--window-size=1366,768")
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        try:
            log(f"[Conta {index}] Iniciando login para {username}...", Fore.CYAN)
            driver.get("https://habblive.in/")
            wait = WebDriverWait(driver, 25)
            # Fecha banner de cookies se aparecer
            try:
                cookie_banner = wait.until(
                    EC.presence_of_element_located((By.ID, "cookie-law-container"))
                )
                try:
                    accept_btn = cookie_banner.find_element(By.TAG_NAME, "button")
                    driver.execute_script("arguments[0].click();", accept_btn)
                    log(f"[Conta {index}] Banner de cookies fechado.", Fore.MAGENTA)
                except Exception:
                    driver.execute_script("""
                        const el = document.getElementById('cookie-law-container');
                        if (el) el.remove();
                    """)
                    log(f"[Conta {index}] Banner de cookies removido via script.", Fore.MAGENTA)
            except Exception:
                pass
            # Login
            wait.until(EC.presence_of_element_located((By.NAME, "username"))).send_keys(username)
            wait.until(EC.presence_of_element_located((By.NAME, "password"))).send_keys(password)
            btn_login = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, ".btn.big.green.login-button")))
            driver.execute_script("arguments[0].click();", btn_login)
            time.sleep(5)
            driver.get(URL_BIGCLIENT)
            log(f"[Conta {index}] ✅ Online no Big Client.", Fore.GREEN)
            with lock:
                status_contas[index] = "✅ Online"
            if EXECUTAR_ACOES:
                executar_acoes_no_quarto(driver, index)
            # Monitoramento de sessão e reinícios
            while True:
                current_url = driver.current_url
                if current_url != URL_BIGCLIENT:
                    log(f"[Conta {index}] ⚠️ Redirecionado para fora ({current_url}). Relogando...", Fore.YELLOW)
                    driver.quit()
                    time.sleep(2)
                    break
                try:
                    driver.find_element(By.CSS_SELECTOR, ".cursor-pointer.navigation-item.icon.icon-rooms")
                except Exception:
                    log(f"[Conta {index}] ⚠️ Cliente reiniciou, aguardando recarregar...", Fore.YELLOW)
                    try:
                        WebDriverWait(driver, 90).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, ".cursor-pointer.navigation-item.icon.icon-rooms"))
                        )
                        log(f"[Conta {index}] Cliente recarregado.", Fore.GREEN)
                        if EXECUTAR_ACOES:
                            executar_acoes_no_quarto(driver, index)
                    except Exception as e:
                        log(f"[Conta {index}] ❌ Cliente não recarregou a tempo: {repr(e)}", Fore.RED)
                time.sleep(CHECK_INTERVAL)
        except Exception as e:
            log(f"[Conta {index}] ❌ Erro: {repr(e)}", Fore.RED)
            with lock:
                status_contas[index] = "❌ Erro"
            driver.quit()
            time.sleep(5)

# Lê todas as contas (mesmo com buracos)
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

with lock:
    for idx in range(1, len(accounts) + 1):
        status_contas[idx] = "⏳ Iniciando"

painel_thread = threading.Thread(target=painel_status, args=(len(accounts),))
painel_thread.start()

threads = []
for idx, (username, password) in enumerate(accounts, start=1):
    t = threading.Thread(target=iniciar_sessao, args=(username, password, idx))
    t.start()
    threads.append(t)
for t in threads:
    t.join()
painel_thread.join()
