# CÓDIGO TURBINADO - Evita quedas frequentes dos personagens
# Melhorias: Headless new, argumentos Chrome otimizados, melhor tratamento de erros
# Sugestões futuras: persistência de sessão, pool de WebDrivers, healthchecks

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
EXECUTAR_ACOES = False  # True = faz ações no quarto, False = só loga/reloga

# Configurações personalizadas
DONO_QUARTO = "OWNER NAME"         # Nome do dono a ser digitado no filtro
NOME_QUARTO = "ROOM NAME"   # Nome exato (ou parte) do quarto a ser clicado
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

def wait_send_keys_css(driver, css, texto, desc, timeout=30):
    wait = WebDriverWait(driver, timeout)
    elem = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, css)))
    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", elem)
    time.sleep(0.2)
    elem.clear()
    elem.send_keys(texto)

# ---------- Funções principais ----------
def iniciar_sessao(conta_num):
    """Inicia uma sessão do WebDriver otimizada para estabilidade"""
    try:
        # Configurações Chrome otimizadas para estabilidade máxima
        options = Options()
        options.add_argument("--headless=new")  # Novo modo headless mais estável
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-gpu")
        options.add_argument("--remote-allow-origins=*")
        options.add_argument("--disable-background-timer-throttling")
        options.add_argument("--disable-features=VizDisplayCompositor")
        options.add_argument("--enable-automation")
        options.add_argument("--disable-notifications")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-plugins")
        options.add_argument("--disable-images")
        options.add_argument("--disable-javascript")
        options.add_argument("--disable-default-apps")
        options.add_argument("--disable-sync")
        options.add_argument("--no-first-run")
        options.add_argument("--no-default-browser-check")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)

        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

        # Timeouts otimizados
        driver.set_page_load_timeout(60)
        driver.implicitly_wait(10)

        return driver
    except Exception as e:
        log(f"Erro ao inicializar WebDriver para conta {conta_num}: {e}", Fore.RED)
        return None

def fazer_login(driver, username, password):
    """Realiza o login no site"""
    try:
        driver.get(URL_BIGCLIENT)
        time.sleep(3)

        # Login
        wait_send_keys_css(driver, "input[name='credentials.username']", username, "Campo usuário")
        wait_send_keys_css(driver, "input[name='credentials.password']", password, "Campo senha")
        wait_click_css(driver, "input[type='submit']", "Botão login")

        time.sleep(5)

        # Verifica se logou com sucesso
        current_url = driver.current_url
        if "client" in current_url or "hotel" in current_url:
            log(f"Login realizado com sucesso para {username}", Fore.GREEN)
            return True
        else:
            log(f"Falha no login para {username} - URL: {current_url}", Fore.RED)
            return False

    except Exception as e:
        log(f"Erro durante login para {username}: {e}", Fore.RED)
        return False

def entrar_quarto(driver):
    """Entra no quarto especificado"""
    if not EXECUTAR_ACOES:
        return

    try:
        # Clica no Navigator
        wait_click_css(driver, "div[title='Navigator']", "Navigator", 15)
        time.sleep(2)

        # Digita o nome do dono
        wait_send_keys_css(driver, "input.searchfield-input", DONO_QUARTO, "Campo busca dono")
        time.sleep(1)

        # Clica em buscar
        wait_click_css(driver, "button.searchfield-button", "Botão buscar")
        time.sleep(3)

        # Procura e clica no quarto
        quartos = driver.find_elements(By.CSS_SELECTOR, ".room-list .room-item")
        for quarto in quartos:
            nome_elem = quarto.find_element(By.CSS_SELECTOR, ".room-name")
            if NOME_QUARTO.lower() in nome_elem.text.lower():
                driver.execute_script("arguments[0].click();", quarto)
                log(f"Entrando no quarto: {nome_elem.text}", Fore.GREEN)
                time.sleep(3)
                return

        log(f"Quarto '{NOME_QUARTO}' não encontrado", Fore.YELLOW)

    except Exception as e:
        log(f"Erro ao entrar no quarto: {e}", Fore.RED)

def verificar_sessao_ativa(driver):
    """Verifica se a sessão ainda está ativa"""
    try:
        # Verifica se ainda está na página correta
        current_url = driver.current_url
        if "client" not in current_url and "hotel" not in current_url:
            return False

        # Tenta encontrar elementos da interface do jogo
        try:
            driver.find_element(By.CSS_SELECTOR, ".room-canvas, #game-container, .hotel-view")
            return True
        except:
            return False

    except Exception:
        return False

def gerenciar_conta(conta_num, username, password):
    """Gerencia uma conta específica com reconexão automática"""
    driver = None
    reconexoes = 0
    max_reconexoes = 5

    while True:
        try:
            with lock:
                status_contas[conta_num] = "🔄 Conectando"

            # Inicializa o WebDriver se necessário
            if not driver:
                driver = iniciar_sessao(conta_num)
                if not driver:
                    with lock:
                        status_contas[conta_num] = "❌ Erro WebDriver"
                    time.sleep(30)
                    continue

            # Faz login
            if fazer_login(driver, username, password):
                with lock:
                    status_contas[conta_num] = "✅ Online"

                # Entra no quarto se configurado
                entrar_quarto(driver)
                reconexoes = 0  # Reset contador de reconexões

                # Loop de monitoramento
                while True:
                    time.sleep(CHECK_INTERVAL)

                    if not verificar_sessao_ativa(driver):
                        log(f"Sessão perdida para {username}, tentando reconectar...", Fore.YELLOW)
                        with lock:
                            status_contas[conta_num] = "⚠️ Reconectando"
                        break

                    with lock:
                        status_contas[conta_num] = "✅ Online"
            else:
                with lock:
                    status_contas[conta_num] = "❌ Erro Login"
                reconexoes += 1

                if reconexoes >= max_reconexoes:
                    log(f"Máximo de reconexões atingido para {username}", Fore.RED)
                    time.sleep(300)  # Espera 5 minutos antes de tentar novamente
                    reconexoes = 0

                # Fecha o driver para forçar nova inicialização
                if driver:
                    try:
                        driver.quit()
                    except:
                        pass
                    driver = None

                time.sleep(30)

        except Exception as e:
            log(f"Erro na conta {conta_num} ({username}): {e}", Fore.RED)
            with lock:
                status_contas[conta_num] = "❌ Erro"

            # Fecha o driver em caso de erro
            if driver:
                try:
                    driver.quit()
                except:
                    pass
                driver = None

            time.sleep(60)

def main():
    """Função principal"""
    log("🚀 Iniciando sistema de login persistente turbinado", Fore.CYAN)

    # Lê as contas do arquivo
    if not os.path.exists('contas.txt'):
        log("❌ Arquivo 'contas.txt' não encontrado!", Fore.RED)
        log("Crie o arquivo com o formato: usuario:senha (uma por linha)", Fore.YELLOW)
        return

    contas = []
    with open('contas.txt', 'r', encoding='utf-8') as f:
        for linha in f:
            linha = linha.strip()
            if linha and ':' in linha:
                username, password = linha.split(':', 1)
                contas.append((username.strip(), password.strip()))

    if not contas:
        log("❌ Nenhuma conta encontrada no arquivo contas.txt", Fore.RED)
        return

    log(f"📋 {len(contas)} conta(s) carregada(s)", Fore.GREEN)

    # Inicia o painel de status em thread separada
    status_thread = threading.Thread(target=painel_status, args=(len(contas),), daemon=True)
    status_thread.start()

    # Cria uma thread para cada conta
    threads = []
    for i, (username, password) in enumerate(contas, 1):
        thread = threading.Thread(
            target=gerenciar_conta,
            args=(i, username, password),
            daemon=True
        )
        threads.append(thread)
        thread.start()

        # Delay entre inicializações para evitar sobrecarga
        time.sleep(5)

    try:
        # Mantém o programa rodando
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        log("🛑 Encerrando sistema...", Fore.RED)

if __name__ == "__main__":
    main()
