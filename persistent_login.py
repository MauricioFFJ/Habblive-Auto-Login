import os
import time
import json
import threading
import urllib.request
import urllib.error
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC

from webdriver_manager.chrome import ChromeDriverManager
from colorama import Fore, Style, init


# ============================================================
# CONFIGURAÇÃO
# ============================================================

URL_BIGCLIENT = "https://habblive.in/bigclient/"

CHECK_INTERVAL = 15

# True = as contas entram automaticamente no quarto configurado.
EXECUTAR_ACOES = True

DONO_QUARTO = "Mist"
NOME_QUARTO = "Picnic - Encontre seu 🎁"


# ============================================================
# SISTEMA DE COMANDOS
# ============================================================

COMMAND_POLL_INTERVAL = 5

GITHUB_API_URL = (
    "https://api.github.com/repos/"
    f"{os.getenv('GITHUB_REPOSITORY', 'MauricioFFJ/Habblive-Auto-Login')}"
    "/contents/commands"
)

GITHUB_TOKEN = (
    os.getenv("COMMAND_GITHUB_TOKEN")
    or os.getenv("GITHUB_TOKEN")
)

# Comandos que este processo já viu.
comandos_processados = set()

# Drivers que estão efetivamente dentro do quarto.
#
# Exemplo:
# {
#     1: driver_conta_1,
#     2: driver_conta_2
# }
drivers_ativos = {}

drivers_lock = threading.Lock()
commands_lock = threading.Lock()


# ============================================================
# INICIALIZAÇÃO
# ============================================================

init(autoreset=True)

status_contas = {}
lock = threading.Lock()


# ============================================================
# LOG
# ============================================================

def log(msg, color=Fore.WHITE):
    timestamp = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    print(
        f"{color}[{timestamp}] "
        f"{msg}"
        f"{Style.RESET_ALL}"
    )


def painel_status(total_contas):
    while True:

        with lock:

            status_parts = []

            for i in range(1, total_contas + 1):

                estado = status_contas.get(
                    i,
                    "⏳ Iniciando"
                )

                status_parts.append(
                    f"[Conta {i}] {estado}"
                )

            painel = " | ".join(status_parts)

        log(
            painel,
            Fore.BLUE
        )

        time.sleep(5)


# ============================================================
# HELPERS SELENIUM
# ============================================================

def wait_click_css(
    driver,
    css,
    desc,
    timeout=30,
    use_js=False
):
    wait = WebDriverWait(
        driver,
        timeout
    )

    elem = wait.until(
        EC.element_to_be_clickable(
            (
                By.CSS_SELECTOR,
                css
            )
        )
    )

    try:
        driver.execute_script(
            """
            arguments[0].scrollIntoView({
                block: 'center'
            });
            """,
            elem
        )
    except Exception:
        pass

    time.sleep(0.2)

    if use_js:

        driver.execute_script(
            "arguments[0].click();",
            elem
        )

    else:

        try:
            elem.click()

        except Exception:

            driver.execute_script(
                "arguments[0].click();",
                elem
            )

    log(
        f"{desc} clicado.",
        Fore.GREEN
    )

    return elem


def wait_click_xpath(
    driver,
    xpath,
    desc,
    timeout=40,
    use_js=False
):
    wait = WebDriverWait(
        driver,
        timeout
    )

    elem = wait.until(
        EC.element_to_be_clickable(
            (
                By.XPATH,
                xpath
            )
        )
    )

    try:
        driver.execute_script(
            """
            arguments[0].scrollIntoView({
                block: 'center'
            });
            """,
            elem
        )
    except Exception:
        pass

    time.sleep(0.2)

    if use_js:

        driver.execute_script(
            "arguments[0].click();",
            elem
        )

    else:

        try:
            elem.click()

        except Exception:

            driver.execute_script(
                "arguments[0].click();",
                elem
            )

    log(
        f"{desc} clicado.",
        Fore.GREEN
    )

    return elem


def wait_type_css(
    driver,
    css,
    text,
    desc,
    timeout=30,
    clear_first=False,
    fire_input=True
):
    wait = WebDriverWait(
        driver,
        timeout
    )

    elem = wait.until(
        EC.presence_of_element_located(
            (
                By.CSS_SELECTOR,
                css
            )
        )
    )

    try:
        driver.execute_script(
            """
            arguments[0].scrollIntoView({
                block: 'center'
            });
            """,
            elem
        )
    except Exception:
        pass

    time.sleep(0.2)

    elem.click()

    if clear_first:

        try:
            elem.clear()

        except Exception:

            try:
                elem.send_keys(
                    Keys.CONTROL,
                    "a"
                )

                elem.send_keys(
                    Keys.BACKSPACE
                )

            except Exception:
                pass

    elem.send_keys(text)

    if fire_input:

        try:

            driver.execute_script(
                """
                arguments[0].dispatchEvent(
                    new Event(
                        'input',
                        {bubbles: true}
                    )
                );

                arguments[0].dispatchEvent(
                    new Event(
                        'change',
                        {bubbles: true}
                    )
                );
                """,
                elem
            )

        except Exception:
            pass

    log(
        f"{desc} digitado: '{text}'.",
        Fore.MAGENTA
    )

    return elem


# ============================================================
# CHAT
# ============================================================

CHAT_INPUT_CSS = (
    ".chat-input[placeholder='Fale aqui...']"
)


def obter_chat_input(
    driver,
    timeout=30
):
    """
    Aguarda o campo real de chat aparecer.
    """

    return WebDriverWait(
        driver,
        timeout
    ).until(
        EC.visibility_of_element_located(
            (
                By.CSS_SELECTOR,
                CHAT_INPUT_CSS
            )
        )
    )


def enviar_chat(
    driver,
    texto,
    index
):
    """
    Digita texto no chat e envia com ENTER.
    """

    if texto is None:
        raise ValueError(
            "Texto do chat não informado."
        )

    texto = str(texto)

    if not texto.strip():
        raise ValueError(
            "Texto do chat está vazio."
        )

    chat = obter_chat_input(
        driver,
        timeout=30
    )

    try:
        driver.execute_script(
            """
            arguments[0].scrollIntoView({
                block: 'center'
            });

            arguments[0].focus();
            """,
            chat
        )
    except Exception:
        pass

    time.sleep(0.2)

    try:
        chat.click()

    except Exception:

        driver.execute_script(
            "arguments[0].focus();",
            chat
        )

    # Limpa conteúdo anterior.

    try:
        chat.clear()

    except Exception:

        try:

            chat.send_keys(
                Keys.CONTROL,
                "a"
            )

            chat.send_keys(
                Keys.BACKSPACE
            )

        except Exception:
            pass

    chat.send_keys(texto)

    time.sleep(0.15)

    chat.send_keys(
        Keys.ENTER
    )

    log(
        f"[Conta {index}] "
        f"💬 Mensagem enviada: {texto}",
        Fore.MAGENTA
    )


def falar_frase(
    driver,
    frase,
    index
):
    """
    Função 1:
    Digita a frase e pressiona ENTER.
    """

    if not frase:
        raise ValueError(
            "A frase não pode estar vazia."
        )

    enviar_chat(
        driver,
        frase,
        index
    )


# ============================================================
# CHOOSER
# ============================================================

CHOOSER_SELECT_CSS = (
    "select.form-select.form-select-sm"
)

CHOOSER_USER_CSS = (
    ".rounded.p-1.bg-muted"
)

CONTEXT_MENU_CSS = (
    ".nitro-context-menu.visible"
)


def abrir_chooser(
    driver,
    index
):
    """
    Envia :chooser e aguarda o chooser.
    """

    enviar_chat(
        driver,
        ":chooser",
        index
    )

    WebDriverWait(
        driver,
        15
    ).until(
        EC.presence_of_element_located(
            (
                By.CSS_SELECTOR,
                CHOOSER_SELECT_CSS
            )
        )
    )

    log(
        f"[Conta {index}] "
        f"Chooser aberto.",
        Fore.CYAN
    )


def selecionar_lives(
    driver,
    index
):
    """
    Seleciona:
        <option value="live">Live</option>
    """

    select_elem = WebDriverWait(
        driver,
        15
    ).until(
        EC.presence_of_element_located(
            (
                By.CSS_SELECTOR,
                CHOOSER_SELECT_CSS
            )
        )
    )

    Select(
        select_elem
    ).select_by_value("live")

    # Dispara change para interfaces React.
    try:

        driver.execute_script(
            """
            arguments[0].dispatchEvent(
                new Event(
                    'change',
                    {bubbles: true}
                )
            );
            """,
            select_elem
        )

    except Exception:
        pass

    log(
        f"[Conta {index}] "
        f"Filtro 'Live' selecionado.",
        Fore.GREEN
    )

    time.sleep(1)


def procurar_usuario(
    driver,
    nome_usuario,
    index
):
    """
    Procura o usuário dentro de:
        .rounded.p-1.bg-muted
    """

    nome_normalizado = (
        str(nome_usuario)
        .strip()
        .casefold()
    )

    if not nome_normalizado:
        raise ValueError(
            "Nome do usuário vazio."
        )

    wait = WebDriverWait(
        driver,
        20
    )

    def localizar(d):

        elementos = d.find_elements(
            By.CSS_SELECTOR,
            CHOOSER_USER_CSS
        )

        for elem in elementos:

            try:

                if not elem.is_displayed():
                    continue

                texto = (
                    elem.text
                    .strip()
                    .casefold()
                )

                if texto == nome_normalizado:
                    return elem

                if nome_normalizado in texto:
                    return elem

            except Exception:
                continue

        return False

    usuario = wait.until(
        localizar
    )

    log(
        f"[Conta {index}] "
        f"Usuário '{nome_usuario}' encontrado.",
        Fore.GREEN
    )

    return usuario


def clicar_usuario(
    driver,
    nome_usuario,
    index
):
    """
    Localiza e clica no usuário.
    """

    usuario = procurar_usuario(
        driver,
        nome_usuario,
        index
    )

    try:

        driver.execute_script(
            """
            arguments[0].scrollIntoView({
                block: 'center'
            });
            """,
            usuario
        )

    except Exception:
        pass

    time.sleep(0.3)

    try:

        usuario.click()

    except Exception:

        driver.execute_script(
            "arguments[0].click();",
            usuario
        )

    log(
        f"[Conta {index}] "
        f"Usuário '{nome_usuario}' selecionado.",
        Fore.GREEN
    )

    return usuario


# ============================================================
# MENU DE CONTEXTO
# ============================================================

def encontrar_acao_contexto(
    driver,
    nome_acao
):
    """
    Procura a ação dentro de:
        .nitro-context-menu.visible
    """

    nome_normalizado = (
        nome_acao
        .strip()
        .casefold()
    )

    menus = driver.find_elements(
        By.CSS_SELECTOR,
        CONTEXT_MENU_CSS
    )

    for menu in menus:

        try:

            if not menu.is_displayed():
                continue

            elementos = menu.find_elements(
                By.XPATH,
                ".//*"
            )

            for elemento in elementos:

                try:

                    if not elemento.is_displayed():
                        continue

                    texto = (
                        elemento.text
                        .strip()
                        .casefold()
                    )

                    if texto == nome_normalizado:
                        return elemento

                except Exception:
                    continue

        except Exception:
            continue

    return None


def clicar_acao_ate_sumir(
    driver,
    nome_acao,
    intervalo,
    index,
    timeout_inicial=15,
    max_cliques=100
):
    """
    Localiza a ação e clica repetidamente até ela desaparecer.

    Respeitar:
        intervalo = 1.0

    Beijar:
        intervalo = 1.1
    """

    def encontrar(d):
        return (
            encontrar_acao_contexto(
                d,
                nome_acao
            )
            or False
        )

    WebDriverWait(
        driver,
        timeout_inicial
    ).until(encontrar)

    cliques = 0

    while cliques < max_cliques:

        elemento = encontrar_acao_contexto(
            driver,
            nome_acao
        )

        if elemento is None:

            log(
                f"[Conta {index}] "
                f"'{nome_acao}' desapareceu.",
                Fore.GREEN
            )

            return

        try:

            driver.execute_script(
                """
                arguments[0].scrollIntoView({
                    block: 'center'
                });
                """,
                elemento
            )

        except Exception:
            pass

        time.sleep(0.15)

        try:

            elemento.click()

        except Exception:

            driver.execute_script(
                "arguments[0].click();",
                elemento
            )

        cliques += 1

        log(
            f"[Conta {index}] "
            f"'{nome_acao}' clicado "
            f"(clique {cliques}).",
            Fore.YELLOW
        )

        time.sleep(intervalo)

    raise RuntimeError(
        f"'{nome_acao}' continuou disponível "
        f"após {max_cliques} cliques."
    )


# ============================================================
# AÇÃO: RESPEITAR
# ============================================================

def respeitar_usuario(
    driver,
    nome_usuario,
    index
):
    """
    :chooser
    ↓
    Live
    ↓
    usuário
    ↓
    Respeitar
    ↓
    cliques a cada 1 segundo
    """

    if not nome_usuario:
        raise ValueError(
            "Nome do usuário não informado."
        )

    log(
        f"[Conta {index}] "
        f"🤝 Iniciando Respeitar em "
        f"'{nome_usuario}'.",
        Fore.CYAN
    )

    abrir_chooser(
        driver,
        index
    )

    selecionar_lives(
        driver,
        index
    )

    clicar_usuario(
        driver,
        nome_usuario,
        index
    )

    clicar_acao_ate_sumir(
        driver,
        "Respeitar",
        1.0,
        index
    )

    log(
        f"[Conta {index}] "
        f"✅ Respeitar concluído para "
        f"'{nome_usuario}'.",
        Fore.GREEN
    )


# ============================================================
# AÇÃO: BEIJAR
# ============================================================

def beijar_usuario(
    driver,
    nome_usuario,
    index
):
    """
    :chooser
    ↓
    Live
    ↓
    usuário
    ↓
    Beijar
    ↓
    cliques a cada 1,1 segundos
    """

    if not nome_usuario:
        raise ValueError(
            "Nome do usuário não informado."
        )

    log(
        f"[Conta {index}] "
        f"💋 Iniciando Beijar em "
        f"'{nome_usuario}'.",
        Fore.CYAN
    )

    abrir_chooser(
        driver,
        index
    )

    selecionar_lives(
        driver,
        index
    )

    clicar_usuario(
        driver,
        nome_usuario,
        index
    )

    clicar_acao_ate_sumir(
        driver,
        "Beijar",
        1.1,
        index
    )

    log(
        f"[Conta {index}] "
        f"✅ Beijar concluído para "
        f"'{nome_usuario}'.",
        Fore.GREEN
    )


# ============================================================
# TARGETS
# ============================================================

def conta_alvo(
    index,
    targets
):
    """
    Verifica se a conta deve executar o comando.

    Exemplos:

        "all"

        [1, 2, 3]

        ["1", "2"]

        "1,2,3"
    """

    if targets is None:
        return True

    if targets == "all":
        return True

    if isinstance(
        targets,
        str
    ):

        targets = [
            item.strip()
            for item in targets.split(",")
            if item.strip()
        ]

    try:

        targets_int = {
            int(x)
            for x in targets
        }

    except Exception:

        return False

    return index in targets_int


# ============================================================
# EXECUÇÃO DOS COMANDOS
# ============================================================

def executar_comando(
    driver,
    comando,
    index
):
    """
    Dispatcher central.
    """

    action = str(
        comando.get(
            "action",
            ""
        )
    ).strip().lower()

    targets = comando.get(
        "targets",
        "all"
    )

    if not conta_alvo(
        index,
        targets
    ):
        return

    log(
        f"[Conta {index}] "
        f"📥 Executando comando: "
        f"{action}",
        Fore.CYAN
    )

    if action == "say":

        frase = comando.get(
            "message",
            ""
        )

        falar_frase(
            driver,
            frase,
            index
        )

    elif action == "respect":

        nome_usuario = comando.get(
            "username",
            ""
        )

        respeitar_usuario(
            driver,
            nome_usuario,
            index
        )

    elif action == "kiss":

        nome_usuario = comando.get(
            "username",
            ""
        )

        beijar_usuario(
            driver,
            nome_usuario,
            index
        )

    else:

        raise ValueError(
            f"Ação desconhecida: {action}"
        )


# ============================================================
# GITHUB API
# ============================================================

def github_request(url):
    """
    Consulta a API do GitHub.
    """

    if not GITHUB_TOKEN:

        raise RuntimeError(
            "GITHUB_TOKEN/COMMAND_GITHUB_TOKEN "
            "não configurado."
        )

    request = urllib.request.Request(
        url,
        headers={
            "Accept":
                "application/vnd.github+json",

            "Authorization":
                f"Bearer {GITHUB_TOKEN}",

            "X-GitHub-Api-Version":
                "2022-11-28",

            "User-Agent":
                "Habblive-Auto-Login"
        }
    )

    with urllib.request.urlopen(
        request,
        timeout=15
    ) as response:

        return json.loads(
            response.read().decode(
                "utf-8"
            )
        )


def listar_comandos():
    """
    Lista commands/*.json.
    """

    try:

        dados = github_request(
            GITHUB_API_URL
        )

    except Exception as e:

        log(
            f"⚠️ Erro ao consultar comandos: "
            f"{repr(e)}",
            Fore.YELLOW
        )

        return []

    if not isinstance(
        dados,
        list
    ):
        return []

    comandos = []

    for item in dados:

        try:

            nome = item.get(
                "name",
                ""
            )

            if not nome.endswith(
                ".json"
            ):
                continue

            download_url = item.get(
                "download_url"
            )

            if not download_url:
                continue

            comandos.append(
                (
                    nome,
                    download_url
                )
            )

        except Exception:
            continue

    return comandos


def baixar_comando(
    download_url
):
    """
    Baixa o JSON do comando.
    """

    try:

        request = urllib.request.Request(
            download_url,
            headers={
                "User-Agent":
                    "Habblive-Auto-Login"
            }
        )

        with urllib.request.urlopen(
            request,
            timeout=15
        ) as response:

            return json.loads(
                response.read().decode(
                    "utf-8"
                )
            )

    except Exception as e:

        log(
            f"⚠️ Erro ao baixar comando: "
            f"{repr(e)}",
            Fore.YELLOW
        )

        return None


def obter_novos_comandos():
    """
    Retorna os comandos ainda não processados.
    """

    novos = []

    arquivos = listar_comandos()

    arquivos.sort(
        key=lambda item: item[0]
    )

    for (
        nome_arquivo,
        download_url
    ) in arquivos:

        if nome_arquivo in comandos_processados:
            continue

        comando = baixar_comando(
            download_url
        )

        if not isinstance(
            comando,
            dict
        ):
            continue

        command_id = str(
            comando.get(
                "id",
                nome_arquivo
            )
        )

        if command_id in comandos_processados:
            continue

        comando["_arquivo"] = (
            nome_arquivo
        )

        comando["_id"] = (
            command_id
        )

        novos.append(
            comando
        )

    return novos


# ============================================================
# EXECUÇÃO DO COMANDO EM UMA CONTA
# ============================================================

def processar_comando_em_conta(
    driver,
    comando,
    index
):
    try:

        executar_comando(
            driver,
            comando,
            index
        )

    except Exception as e:

        log(
            f"[Conta {index}] "
            f"❌ Erro no comando "
            f"{comando.get('_id')}: "
            f"{repr(e)}",
            Fore.RED
        )


# ============================================================
# MONITOR DE COMANDOS
# ============================================================

def monitorar_comandos():
    """
    Monitora a pasta commands/ do GitHub.

    Só executa comandos em drivers registrados em
    drivers_ativos.

    Um driver só é colocado em drivers_ativos depois
    que a conta entra efetivamente no quarto.
    """

    if not GITHUB_TOKEN:

        log(
            "⚠️ GITHUB_TOKEN não disponível. "
            "Controle remoto desativado.",
            Fore.YELLOW
        )

        return

    log(
        "🎮 Monitor de comandos iniciado.",
        Fore.CYAN
    )

    while True:

        try:

            novos = obter_novos_comandos()

            for comando in novos:

                command_id = comando[
                    "_id"
                ]

                with commands_lock:

                    if command_id in (
                        comandos_processados
                    ):
                        continue

                    # Marca antes da execução.
                    comandos_processados.add(
                        command_id
                    )

                action = comando.get(
                    "action"
                )

                targets = comando.get(
                    "targets",
                    "all"
                )

                log(
                    f"📨 Novo comando: "
                    f"{command_id} "
                    f"({action})",
                    Fore.CYAN
                )

                with drivers_lock:

                    drivers = dict(
                        drivers_ativos
                    )

                if not drivers:

                    log(
                        "⏳ Nenhuma conta está "
                        "atualmente dentro do quarto.",
                        Fore.YELLOW
                    )

                    continue

                threads_comando = []

                for (
                    index,
                    driver
                ) in drivers.items():

                    if not conta_alvo(
                        index,
                        targets
                    ):
                        continue

                    thread = threading.Thread(
                        target=processar_comando_em_conta,
                        args=(
                            driver,
                            comando,
                            index
                        ),
                        daemon=True
                    )

                    thread.start()

                    threads_comando.append(
                        thread
                    )

                for thread in (
                    threads_comando
                ):
                    thread.join()

                log(
                    f"📨 Comando "
                    f"{command_id} concluído.",
                    Fore.GREEN
                )

        except Exception as e:

            log(
                f"⚠️ Erro no monitor de comandos: "
                f"{repr(e)}",
                Fore.YELLOW
            )

        time.sleep(
            COMMAND_POLL_INTERVAL
        )


# ============================================================
# FILTRO DE DONO
# ============================================================

def selecionar_opcao_dono(
    driver
):
    select_css = (
        "select.form-select.form-select-sm"
    )

    wait = WebDriverWait(
        driver,
        30
    )

    select_elem = wait.until(
        EC.presence_of_element_located(
            (
                By.CSS_SELECTOR,
                select_css
            )
        )
    )

    driver.execute_script(
        """
        arguments[0].value = '2';

        arguments[0].dispatchEvent(
            new Event(
                'change',
                {bubbles: true}
            )
        );
        """,
        select_elem
    )

    log(
        "Filtro 'Dono' selecionado.",
        Fore.GREEN
    )

    return select_elem


# ============================================================
# LOCALIZAÇÃO DO QUARTO
# ============================================================

def clicar_quarto_por_nome(
    driver,
    nome,
    timeout=40
):
    mapa_maius = (
        "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        "ÁÉÍÓÚÂÊÎÔÛÃÕÇ"
    )

    mapa_minus = (
        "abcdefghijklmnopqrstuvwxyz"
        "áéíóúâêîôûãõç"
    )

    nome_lower = nome.lower()

    xpath_exato = (
        "//div[@class='flex-grow-1 "
        "d-inline text-black "
        "text-truncate' and "
        f"translate("
        f"normalize-space(text()), "
        f"'{mapa_maius}', "
        f"'{mapa_minus}')="
        f"'{nome_lower}']"
    )

    xpath_contains = (
        "//div[@class='flex-grow-1 "
        "d-inline text-black "
        "text-truncate' and "
        f"contains("
        f"translate("
        f"normalize-space(text()), "
        f"'{mapa_maius}', "
        f"'{mapa_minus}'), "
        f"'{nome_lower}')]"
    )

    try:

        return wait_click_xpath(
            driver,
            xpath_exato,
            f"Quarto '{nome}' (exato)",
            timeout=timeout,
            use_js=True
        )

    except Exception as e1:

        log(
            f"Quarto exato não encontrado: "
            f"{repr(e1)}. Tentando contains...",
            Fore.YELLOW
        )

        return wait_click_xpath(
            driver,
            xpath_contains,
            f"Quarto contendo '{nome}'",
            timeout=timeout,
            use_js=True
        )


# ============================================================
# ENTRAR NO QUARTO
# ============================================================

def executar_acoes_no_quarto(
    driver,
    index
):
    """
    Entra no quarto configurado.

    Retorna True somente quando a entrada no quarto
    foi concluída.
    """

    for tentativa in range(
        1,
        4
    ):

        try:

            log(
                f"[Conta {index}] "
                f"Entrando no quarto "
                f"(tentativa "
                f"{tentativa}/3)...",
                Fore.YELLOW
            )

            time.sleep(15)

            # Abrir navegador de quartos.

            wait_click_css(
                driver,
                ".cursor-pointer.navigation-item."
                "icon.icon-rooms",
                "[Navegador de Quartos]",
                timeout=30,
                use_js=True
            )

            time.sleep(4)

            # Abrir filtro.

            wait_click_css(
                driver,
                "select.form-select.form-select-sm",
                "[Menu de filtro]",
                timeout=30,
                use_js=True
            )

            time.sleep(1)

            # Dono.

            selecionar_opcao_dono(
                driver
            )

            time.sleep(2)

            # Campo de busca.

            wait_type_css(
                driver,
                "input.form-control.form-control-sm"
                "[placeholder='filtrar quartos por']",
                DONO_QUARTO,
                "[Filtro de texto - dono]",
                timeout=30,
                clear_first=True,
                fire_input=True
            )

            time.sleep(2)

            # Buscar.

            wait_click_css(
                driver,
                ".d-flex.align-items-center."
                "justify-content-center.btn."
                "btn-primary.btn-sm",
                "[Botão Buscar]",
                timeout=30,
                use_js=True
            )

            time.sleep(10)

            # Quarto.

            clicar_quarto_por_nome(
                driver,
                NOME_QUARTO,
                timeout=45
            )

            log(
                f"[Conta {index}] "
                f"Entrando no quarto "
                f"'{NOME_QUARTO}'.",
                Fore.GREEN
            )

            # ------------------------------------------------
            # AGUARDA O CHAT DO QUARTO
            # ------------------------------------------------

            log(
                f"[Conta {index}] "
                f"Aguardando chat do quarto...",
                Fore.YELLOW
            )

            obter_chat_input(
                driver,
                timeout=60
            )

            log(
                f"[Conta {index}] "
                f"✅ Chat do quarto disponível.",
                Fore.GREEN
            )

            return True

        except Exception as e:

            log(
                f"[Conta {index}] "
                f"❌ Falha ao entrar no quarto: "
                f"{repr(e)}",
                Fore.RED
            )

            if tentativa < 3:

                time.sleep(6)

                try:

                    wait_click_css(
                        driver,
                        ".cursor-pointer.navigation-item."
                        "icon.icon-rooms",
                        "[Reabrir Navegador de Quartos]",
                        timeout=15,
                        use_js=True
                    )

                except Exception as e2:

                    log(
                        f"[Conta {index}] "
                        f"Não conseguiu reabrir navegador: "
                        f"{repr(e2)}",
                        Fore.YELLOW
                    )

            else:

                log(
                    f"[Conta {index}] "
                    f"❌ Entrada no quarto falhou "
                    f"após 3 tentativas.",
                    Fore.RED
                )

    return False


# ============================================================
# SESSÃO
# ============================================================

def iniciar_sessao(
    username,
    password,
    index
):
    """
    Mantém uma conta online.

    O driver só entra em drivers_ativos depois que
    o quarto e o chat estão disponíveis.
    """

    time.sleep(
        index * 3
    )

    while True:

        with lock:

            status_contas[index] = (
                "🔄 Relogando"
            )

        options = Options()

        options.add_argument(
            "--headless=new"
        )

        options.add_argument(
            "--no-sandbox"
        )

        options.add_argument(
            "--disable-dev-shm-usage"
        )

        options.add_argument(
            "--incognito"
        )

        options.add_argument(
            "--window-size=1366,768"
        )

        service = Service(
            ChromeDriverManager().install()
        )

        driver = webdriver.Chrome(
            service=service,
            options=options
        )

        quarto_aberto = False

        try:

            log(
                f"[Conta {index}] "
                f"Iniciando login para "
                f"{username}...",
                Fore.CYAN
            )

            driver.get(
                "https://habblive.in/"
            )

            wait = WebDriverWait(
                driver,
                25
            )

            # =================================================
            # COOKIES
            # =================================================

            try:

                cookie_banner = wait.until(
                    EC.presence_of_element_located(
                        (
                            By.ID,
                            "cookie-law-container"
                        )
                    )
                )

                try:

                    accept_btn = (
                        cookie_banner.find_element(
                            By.TAG_NAME,
                            "button"
                        )
                    )

                    driver.execute_script(
                        "arguments[0].click();",
                        accept_btn
                    )

                    log(
                        f"[Conta {index}] "
                        f"Banner de cookies fechado.",
                        Fore.MAGENTA
                    )

                except Exception:

                    driver.execute_script(
                        """
                        const el =
                            document.getElementById(
                                'cookie-law-container'
                            );

                        if (el) {
                            el.remove();
                        }
                        """
                    )

                    log(
                        f"[Conta {index}] "
                        f"Banner de cookies removido.",
                        Fore.MAGENTA
                    )

            except Exception:
                pass

            # =================================================
            # LOGIN
            # =================================================

            wait.until(
                EC.presence_of_element_located(
                    (
                        By.NAME,
                        "username"
                    )
                )
            ).send_keys(
                username
            )

            wait.until(
                EC.presence_of_element_located(
                    (
                        By.NAME,
                        "password"
                    )
                )
            ).send_keys(
                password
            )

            btn_login = wait.until(
                EC.element_to_be_clickable(
                    (
                        By.CSS_SELECTOR,
                        ".btn.big.green.login-button"
                    )
                )
            )

            driver.execute_script(
                "arguments[0].click();",
                btn_login
            )

            time.sleep(5)

            driver.get(
                URL_BIGCLIENT
            )

            log(
                f"[Conta {index}] "
                f"✅ Big Client carregado.",
                Fore.GREEN
            )

            with lock:

                status_contas[index] = (
                    "🌐 Big Client"
                )

            # =================================================
            # ENTRADA AUTOMÁTICA NO QUARTO
            # =================================================

            if EXECUTAR_ACOES:

                quarto_aberto = (
                    executar_acoes_no_quarto(
                        driver,
                        index
                    )
                )

            # =================================================
            # REGISTRA COMO ATIVO SOMENTE AGORA
            # =================================================

            if quarto_aberto:

                with drivers_lock:

                    drivers_ativos[index] = (
                        driver
                    )

                with lock:

                    status_contas[index] = (
                        "🏠 No quarto"
                    )

                log(
                    f"[Conta {index}] "
                    f"🏠 Driver registrado como ativo.",
                    Fore.GREEN
                )

            else:

                with lock:

                    status_contas[index] = (
                        "⚠️ Fora do quarto"
                    )

                log(
                    f"[Conta {index}] "
                    f"⚠️ Conta não foi registrada "
                    f"como ativa.",
                    Fore.YELLOW
                )

            # =================================================
            # MONITORAMENTO DA SESSÃO
            # =================================================

            while True:

                current_url = (
                    driver.current_url
                )

                # ---------------------------------------------
                # REDIRECIONAMENTO
                # ---------------------------------------------

                if current_url != URL_BIGCLIENT:

                    try:

                        driver.find_element(
                            By.CSS_SELECTOR,
                            ".cursor-pointer."
                            "navigation-item."
                            "icon.icon-rooms"
                        )

                    except Exception:

                        log(
                            f"[Conta {index}] "
                            f"⚠️ Cliente saiu "
                            f"({current_url}). "
                            f"Relogando...",
                            Fore.YELLOW
                        )

                        with drivers_lock:

                            drivers_ativos.pop(
                                index,
                                None
                            )

                        try:
                            driver.quit()
                        except Exception:
                            pass

                        time.sleep(2)

                        break

                # ---------------------------------------------
                # VERIFICA SE O CLIENTE AINDA EXISTE
                # ---------------------------------------------

                try:

                    driver.find_element(
                        By.CSS_SELECTOR,
                        ".cursor-pointer."
                        "navigation-item."
                        "icon.icon-rooms"
                    )

                except Exception:

                    log(
                        f"[Conta {index}] "
                        f"⚠️ Cliente reiniciou. "
                        f"Aguardando recarregar...",
                        Fore.YELLOW
                    )

                    # Enquanto está recarregando,
                    # não pode receber comandos.

                    with drivers_lock:

                        drivers_ativos.pop(
                            index,
                            None
                        )

                    quarto_aberto = False

                    try:

                        WebDriverWait(
                            driver,
                            90
                        ).until(
                            EC.presence_of_element_located(
                                (
                                    By.CSS_SELECTOR,
                                    ".cursor-pointer."
                                    "navigation-item."
                                    "icon.icon-rooms"
                                )
                            )
                        )

                        log(
                            f"[Conta {index}] "
                            f"Cliente recarregado.",
                            Fore.GREEN
                        )

                        if EXECUTAR_ACOES:

                            quarto_aberto = (
                                executar_acoes_no_quarto(
                                    driver,
                                    index
                                )
                            )

                        if quarto_aberto:

                            with drivers_lock:

                                drivers_ativos[index] = (
                                    driver
                                )

                            with lock:

                                status_contas[index] = (
                                    "🏠 No quarto"
                                )

                    except Exception as e:

                        log(
                            f"[Conta {index}] "
                            f"❌ Cliente não recarregou: "
                            f"{repr(e)}",
                            Fore.RED
                        )

                time.sleep(
                    CHECK_INTERVAL
                )

        except Exception as e:

            log(
                f"[Conta {index}] "
                f"❌ Erro geral: "
                f"{repr(e)}",
                Fore.RED
            )

            with drivers_lock:

                drivers_ativos.pop(
                    index,
                    None
                )

            with lock:

                status_contas[index] = (
                    "❌ Erro"
                )

            try:
                driver.quit()
            except Exception:
                pass

            time.sleep(5)


# ============================================================
# LEITURA DAS CONTAS
# ============================================================

accounts = []

i = 1

while i <= 100:

    user = os.getenv(
        f"HABBLIVE_USERNAME_{i}"
    )

    pwd = os.getenv(
        f"HABBLIVE_PASSWORD_{i}"
    )

    if user and pwd:

        accounts.append(
            (
                user,
                pwd
            )
        )

    i += 1


if not accounts:

    raise ValueError(
        "Nenhuma conta configurada nos secrets."
    )


# ============================================================
# STATUS INICIAL
# ============================================================

with lock:

    for idx in range(
        1,
        len(accounts) + 1
    ):

        status_contas[idx] = (
            "⏳ Iniciando"
        )


# ============================================================
# PAINEL
# ============================================================

painel_thread = threading.Thread(
    target=painel_status,
    args=(
        len(accounts),
    ),
    daemon=True
)

painel_thread.start()


# ============================================================
# MONITOR DE COMANDOS
# ============================================================

command_thread = threading.Thread(
    target=monitorar_comandos,
    daemon=True
)

command_thread.start()


# ============================================================
# THREADS DAS CONTAS
# ============================================================

threads = []

for idx, (
    username,
    password
) in enumerate(
    accounts,
    start=1
):

    t = threading.Thread(
        target=iniciar_sessao,
        args=(
            username,
            password,
            idx
        )
    )

    t.start()

    threads.append(
        t
    )


# ============================================================
# MANTÉM TUDO VIVO
# ============================================================

for t in threads:

    t.join()

painel_thread.join()
command_thread.join()
