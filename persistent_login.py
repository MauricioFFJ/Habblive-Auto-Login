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
BASE_URL = "https://hubbe.biz/"
LOGIN_URL = "https://hubbe.biz/login"
ME_URL = "https://hubbe.biz/me"
PLAY_URL = "https://hubbe.biz/jogar"
CHECK_INTERVAL = 15  # segundos entre verificações
WINDOW_SIZE = "1366,768"

# Fluxos e opções
EXECUTAR_ACOES = True            # True = filtrar e entrar no quarto, False = só loga
AUTO_RENEW_WORKFLOW = True       # Recomeça o workflow ao encerrar (por erro, recaptcha, etc.)
AUTO_RELOAD_PLAY = True          # Recarrega /jogar em caso de inatividade
AUTO_RELOAD_INTERVAL = 300       # segundos para recarregar /jogar automaticamente
DETECTAR_CLOUDFLARE_RECAPTCHA = True  # encerra workflow ao detectar desafio

# Filtros de quarto
DONO_QUARTO = "OWNER_NICK"       # Dono para filtro (personalizável)
NOME_QUARTO = "ROOM_NAME"        # Nome do quarto (exato ou parte, personalizável)

# Mensagens no chat (opcional)
ENVIAR_MENSAGENS = False         # ativa/desativa envio automático
MENSAGEM_TEXTO = "Olá a todos!"  # texto da mensagem
MENSAGEM_INTERVALO = 60          # reenvio a cada X segundos

# Promover Quarto (opcional)
PROMOVER_QUARTO = False          # ativa/desativa fluxo de promoção
PROMO_TITULO = "EVENTO"          # texto do input de título
PROMO_DESCRICAO = "-"            # texto do textarea de descrição
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
def wait_click_css(driver, css, desc, timeout=30, use_js=False, center=True):
    wait = WebDriverWait(driver, timeout)
    elem = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, css)))
    if center:
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
    # value=2 corresponde à opção "Dono"
    driver.execute_script("""
        arguments[0].value = '2';
        arguments[0].dispatchEvent(new Event('change', { bubbles: true }));
    """, select_elem)
    log("Filtro 'Dono' selecionado (via change event).", Fore.GREEN)
    return select_elem


def clicar_quarto_por_nome(driver, nome, timeout=45):
    # Case-insensitive e com acentos, tenta exato e depois contains
    mapa_maius = "ABCDEFGHIJKLMNOPQRSTUVWXYZÁÉÍÓÚÂÊÎÔÛÃÕÇ"
    mapa_minus = "abcdefghijklmnopqrstuvwxyzáéíóúâêîôûãõç"
    nome_lower = nome.lower()

    xpath_exato = (
        f"//div[contains(@class,'flex-grow-1') and contains(@class,'text-truncate') and "
        f"translate(normalize-space(text()), '{mapa_maius}', '{mapa_minus}')='{nome_lower}']"
    )
    xpath_contains = (
        f"//div[contains(@class,'flex-grow-1') and contains(@class,'text-truncate') and "
        f"contains(translate(normalize-space(text()), '{mapa_maius}', '{mapa_minus}'), '{nome_lower}')]"
    )

    try:
        return wait_click_xpath(driver, xpath_exato, f"Quarto '{nome}' (exato)", timeout=timeout, use_js=True)
    except Exception as e1:
        log(f"Quarto exato não encontrado: {repr(e1)}. Tentando por 'contém'...", Fore.YELLOW)
        return wait_click_xpath(driver, xpath_contains, f"Quarto contendo '{nome}'", timeout=timeout, use_js=True)


def detecta_recaptcha_ou_cloudflare(driver):
    if not DETECTAR_CLOUDFLARE_RECAPTCHA:
        return False
    try:
        # recaptcha iframe comum
        iframes = driver.find_elements(By.CSS_SELECTOR, "iframe[src*='recaptcha'], iframe[title*='recaptcha']")
        if iframes:
            return True
    except Exception:
        pass
    try:
        # Padrões de páginas de verificação Cloudflare
        cf_texts = [
            "Checking your browser", "Verifying", "Cloudflare", "Just a moment"
        ]
        body_text = driver.find_element(By.TAG_NAME, "body").text.lower()
        if any(t.lower() in body_text for t in cf_texts):
            return True
    except Exception:
        pass
    return False


def login_hubbe(driver, username, password, index):
    log(f"[Conta {index}] Acessando {BASE_URL}...", Fore.CYAN)
    driver.get(BASE_URL)
    WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.TAG_NAME, "body")))

    # Aguarda redirecionar para /login
    try:
        WebDriverWait(driver, 15).until(EC.url_contains("/login"))
    except Exception:
        # Se não redirecionou, forçamos
        driver.get(LOGIN_URL)

    if detecta_recaptcha_ou_cloudflare(driver):
        raise RuntimeError("Desafio de recaptcha/Cloudflare detectado.")

    # Preenche username e password pelos IDs
    wait = WebDriverWait(driver, 25)
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input#username[name='username']"))).send_keys(username)
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input#password[name='password']"))).send_keys(password)

    # Aguarda ~10s
    time.sleep(10)

    # Clica botão Entrar (usa texto do span e classes comuns)
    try:
        entrar_btn = wait.until(EC.element_to_be_clickable((
            By.XPATH,
            "//button[.//span[normalize-space(text())='Entrar']]"
        )))
        driver.execute_script("arguments[0].click();", entrar_btn)
    except Exception:
        # fallback via classe distintiva
        wait_click_css(driver,
                       "button.buttonGreen",
                       "[Botão Entrar]", timeout=20, use_js=True)

    # Verifica desafios novamente
    time.sleep(3)
    if detecta_recaptcha_ou_cloudflare(driver):
        raise RuntimeError("Desafio de recaptcha/Cloudflare após tentar logar.")

    # Aguarda redirecionar para /me
    WebDriverWait(driver, 30).until(EC.url_contains("/me"))
    log(f"[Conta {index}] ✅ Login efetuado e redirecionado para /me.", Fore.GREEN)


def entrar_no_jogo(driver, index):
    # Botão Jogar agora
    wait_click_xpath(
        driver,
        "//button[contains(@class,'bg-[rgba(95,186,58,1)') and normalize-space(text())='Jogar agora']",
        "[Jogar agora]",
        timeout=30,
        use_js=True
    )
    # Aguarda até que o cliente carregue (ícone de quartos aparece)
    WebDriverWait(driver, 60).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, ".cursor-pointer.navigation-item.icon.icon-rooms"))
    )
    log(f"[Conta {index}] Cliente carregado.", Fore.GREEN)


def abrir_navegador_quartos_e_filtrar(driver, index, dono_quarto):
    # Abre navegador de quartos
    wait_click_css(driver, ".cursor-pointer.navigation-item.icon.icon-rooms",
                   "[Navegador de Quartos]", timeout=30, use_js=True)
    time.sleep(2)

    # Seleciona 'Dono'
    selecionar_opcao_dono(driver)
    time.sleep(1.5)

    # Digita dono
    wait_type_css(driver,
                  "input.form-control.form-control-sm[placeholder='filtrar quartos por']",
                  dono_quarto, "[Filtro de texto - dono]",
                  timeout=30, clear_first=True, fire_input=True)
    time.sleep(1.2)

    # Botão buscar
    wait_click_css(driver,
                   ".d-flex.align-items-center.justify-content-center.btn.btn-primary.btn-sm",
                   "[Botão Buscar]", timeout=30, use_js=True)
    time.sleep(2)


def executar_fluxo_entrar_no_quarto(driver, index, dono_quarto, nome_quarto):
    abrir_navegador_quartos_e_filtrar(driver, index, dono_quarto)
    clicar_quarto_por_nome(driver, nome_quarto, timeout=45)
    log(f"[Conta {index}] Entrando no quarto '{nome_quarto}'.", Fore.GREEN)
    from selenium.webdriver.common.keys import Keys

def chat_auto_loop(driver, index, mensagem, intervalo, stop_event):
    while not stop_event.is_set():
        try:
            # Campo de chat
            chat_input = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "input.chat-input[placeholder='Fale aqui...']"))
            )
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", chat_input)
            chat_input.click()
            chat_input.send_keys(mensagem)
            chat_input.send_keys(Keys.ENTER)
            log(f"[Conta {index}] Mensagem enviada: {mensagem}", Fore.MAGENTA)
        except Exception as e:
            log(f"[Conta {index}] Falha ao enviar mensagem: {repr(e)}", Fore.YELLOW)
        # Aguarda intervalo
        stop_event.wait(intervalo)


def tentar_promover_quarto(driver, index, promo_titulo, promo_desc):
    try:
        # Notificação "Promover Quarto"
        wait_click_xpath(driver,
            "//div[contains(@class,'nitro-notification-bubble')]//div[contains(@class,'cursor-pointer')]"
            "[.//div[contains(@class,'icon-small-room')] and .//div[normalize-space(text())='Promover Quarto']]",
            "[Promover Quarto - notificação]", timeout=10, use_js=True
        )
    except Exception as e:
        log(f"[Conta {index}] Notificação de Promover Quarto não encontrada/ignorável: {repr(e)}", Fore.YELLOW)
        return False

    ok = False
    try:
        # Input título
        wait_type_css(driver,
                      "input.form-control.form-control-sm[maxlength='64']",
                      promo_titulo, "[Promo - título]", timeout=15,
                      clear_first=True, fire_input=True)
        time.sleep(0.5)
        # Textarea descrição
        wait = WebDriverWait(driver, 10)
        textarea = wait.until(EC.presence_of_element_located(
            (By.CSS_SELECTOR, "textarea.form-control.form-control-sm[maxlength='100']")
        ))
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", textarea)
        textarea.click()
        textarea.clear()
        textarea.send_keys(promo_desc)
        log("[Promo - descrição] digitada.", Fore.MAGENTA)
        ok = True
    except Exception as e:
        log(f"[Conta {index}] Campos de promoção não disponíveis, ignorando: {repr(e)}", Fore.YELLOW)

    return ok


def copiar_nome_quarto_via_preferencias(driver, index):
    # Abre Preferências
    wait_click_css(driver, "div.cursor-pointer.icon.icon-cog[title='Preferências']",
                   "[Preferências]", timeout=20, use_js=True)
    time.sleep(1)

    # Captura nome do quarto
    wait = WebDriverWait(driver, 20)
    nome_elem = wait.until(EC.presence_of_element_located((
        By.XPATH,
        "//div[contains(@class,'nitro-text') and contains(@class,'fw-bold') and normalize-space(text())]"
    )))
    nome_quarto = nome_elem.text.strip()
    log(f"[Preferências] Nome do quarto detectado: {nome_quarto}", Fore.CYAN)

    # Fecha card de Informações do Quarto
    wait_click_xpath(
        driver,
        "//span[normalize-space(text())='Informações do Quarto']/ancestor::*[contains(@class,'nitro-card')]"
        "//div[contains(@class,'nitro-card-header-close')]",
        "[Fechar Informações do Quarto]",
        timeout=15, use_js=True
    )

    return nome_quarto


def promover_comprar(driver, index, nome_quarto):
    # Localiza select "Selecione um Quarto"
    wait = WebDriverWait(driver, 20)
    select_elem = wait.until(EC.presence_of_element_located((
        By.XPATH,
        "//select[contains(@class,'form-select') and contains(@class,'form-select-sm')]"
        "[option[@value='-1' and @disabled]] | //select[contains(@class,'form-select') and contains(@class,'form-select-sm')]"
    )))
    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", select_elem)
    time.sleep(0.3)

    # Seleciona a opção cujo texto visível corresponde ao nome do quarto
    options = select_elem.find_elements(By.TAG_NAME, "option")
    alvo = None
    for opt in options:
        label = opt.text.strip()
        if label.lower() == nome_quarto.lower():
            alvo = opt
            break

    if not alvo:
        log(f"[Conta {index}] Opção do quarto '{nome_quarto}' não encontrada no select.", Fore.YELLOW)
        return False

    driver.execute_script("arguments[0].selected = true;", alvo)
    driver.execute_script("""
        arguments[0].dispatchEvent(new Event('change', { bubbles: true }));
    """, select_elem)
    log(f"[Conta {index}] Quarto selecionado para promoção: {nome_quarto}", Fore.GREEN)

    # Clica Comprar
    wait_click_css(driver,
                   "div.d-flex.align-items-center.justify-content-center.btn.btn-success.btn-sm",
                   "[Comprar promoção]", timeout=15, use_js=True)
    log(f"[Conta {index}] Promoção acionada.", Fore.GREEN)
    return True


def manter_sessao(driver, index, stop_event):
    # Recarrega /jogar por inatividade e também de forma periódica
    last_reload = time.time()

    while not stop_event.is_set():
        current_url = driver.current_url

        # Se caiu para fora do cliente, tenta voltar
        try:
            driver.find_element(By.CSS_SELECTOR, ".cursor-pointer.navigation-item.icon.icon-rooms")
            # UI ok
        except Exception:
            # Tenta esperar ela voltar
            log(f"[Conta {index}] ⚠️ Cliente reiniciou, aguardando recarregar...", Fore.YELLOW)
            try:
                WebDriverWait(driver, 90).until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, ".cursor-pointer.navigation-item.icon.icon-rooms")
                    )
                )
                log(f"[Conta {index}] Cliente recarregado.", Fore.GREEN)
            except Exception as e:
                log(f"[Conta {index}] ❌ Cliente não recarregou a tempo: {repr(e)}", Fore.RED)

        # Auto-reload da página /jogar
        if AUTO_RELOAD_PLAY and (time.time() - last_reload >= AUTO_RELOAD_INTERVAL):
            log(f"[Conta {index}] Recarregando {PLAY_URL} por rotina...", Fore.CYAN)
            try:
                driver.get(PLAY_URL)
                WebDriverWait(driver, 60).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".cursor-pointer.navigation-item.icon.icon-rooms"))
                )
                last_reload = time.time()
                log(f"[Conta {index}] /jogar recarregado.", Fore.GREEN)
            except Exception as e:
                log(f"[Conta {index}] Falha ao recarregar /jogar: {repr(e)}", Fore.YELLOW)

        time.sleep(CHECK_INTERVAL)


def iniciar_sessao(username, password, index):
    # Evita colisão de logins
    time.sleep(index * 3)

    while True:
        with lock:
            status_contas[index] = "🔄 Relogando"

        options = Options()
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--incognito")
        options.add_argument(f"--window-size={WINDOW_SIZE}")

        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)

        try:
            login_hubbe(driver, username, password, index)
            # Vai para /me → clica Jogar agora → aguarda cliente
            entrar_no_jogo(driver, index)

            with lock:
                status_contas[index] = "✅ Online"

            # Fluxo de entrar no quarto
            if EXECUTAR_ACOES:
                executar_fluxo_entrar_no_quarto(driver, index, DONO_QUARTO, NOME_QUARTO)

            # Mensagens automáticas
            stop_event = threading.Event()
            chat_thread = None
            if ENVIAR_MENSAGENS:
                chat_thread = threading.Thread(
                    target=chat_auto_loop,
                    args=(driver, index, MENSAGEM_TEXTO, MENSAGEM_INTERVALO, stop_event),
                    daemon=True
                )
                chat_thread.start()

            # Promover Quarto
            if PROMOVER_QUARTO:
                promo_acionada = tentar_promover_quarto(driver, index, PROMO_TITULO, PROMO_DESCRICAO)
                if promo_acionada:
                    try:
                        nome_detectado = copiar_nome_quarto_via_preferencias(driver, index)
                        promover_comprar(driver, index, nome_detectado)
                    except Exception as e:
                        log(f"[Conta {index}] Erro no fluxo de promoção: {repr(e)}", Fore.YELLOW)

            # Manter sessão e rotina de reload
            manter_sessao(driver, index, stop_event)

            # Encerrar threads de chat ao sair
            if stop_event and chat_thread:
                stop_event.set()
                chat_thread.join(timeout=2)

            driver.quit()

            if AUTO_RENEW_WORKFLOW:
                log(f"[Conta {index}] Workflow encerrado. Reiniciando por configuração...", Fore.YELLOW)
                time.sleep(5)
                continue
            else:
                log(f"[Conta {index}] Workflow encerrado. Não renovar.", Fore.YELLOW)
                break

        except RuntimeError as e:
            # recaptcha/Cloudflare ou interrupção intencional
            log(f"[Conta {index}] ❌ Workflow encerrado: {repr(e)}", Fore.RED)
            driver.quit()
            if AUTO_RENEW_WORKFLOW:
                time.sleep(5)
                continue
            break
        except Exception as e:
            log(f"[Conta {index}] ❌ Erro inesperado: {repr(e)}", Fore.RED)
            with lock:
                status_contas[index] = "❌ Erro"
            driver.quit()
            time.sleep(5)
            if AUTO_RENEW_WORKFLOW:
                continue
            break


# Lê todas as contas, mesmo com buracos
accounts = []
i = 1
while i <= 100:
    # Suporta dois esquemas de secrets:
    # 1) HUBBE_USERNAME_i / HUBBE_PASSWORD_i
    # 2) username_i / password_i
    user = os.getenv(f"HUBBE_USERNAME_{i}") or os.getenv(f"username_{i}")
    pwd = os.getenv(f"HUBBE_PASSWORD_{i}") or os.getenv(f"password_{i}")
    if user and pwd:
        accounts.append((user, pwd))
    i += 1

if not accounts:
    raise ValueError("Nenhuma conta configurada nos secrets (HUBBE_USERNAME_i/HUBBE_PASSWORD_i ou username_i/password_i).")

# Inicializa status
with lock:
    for idx in range(1, len(accounts) + 1):
        status_contas[idx] = "⏳ Iniciando"

# Thread do painel
painel_thread = threading.Thread(target=painel_status, args=(len(accounts),), daemon=True)
painel_thread.start()

# Threads das contas
threads = []
for idx, (username, password) in enumerate(accounts, start=1):
    t = threading.Thread(target=iniciar_sessao, args=(username, password, idx), daemon=True)
    t.start()
    threads.append(t)

# Mantém todas as threads vivas
for t in threads:
    t.join()

# Painel (se ainda ativo)
try:
    painel_thread.join(timeout=1)
except:
    pass
