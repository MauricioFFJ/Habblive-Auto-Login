import time
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from colorama import Fore
from persistent_login import log, status_contas, lock

# --- Função auxiliar para digitar e enviar no chat ---
def enviar_chat(driver, texto, desc="[Chat]"):
    wait = WebDriverWait(driver, 20)
    chat_input = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".chat-input")))
    chat_input.click()
    chat_input.send_keys(texto)
    chat_input.send_keys(Keys.ENTER)
    log(f"{desc} enviado: {texto}", Fore.MAGENTA)

# --- 1. Falar uma frase ---
def falar_frase(driver, frase):
    enviar_chat(driver, frase, "[Falar frase]")

# --- 2. Respeitar usuário ---
def respeitar_usuario(driver, nome_usuario):
    # Abrir chooser
    enviar_chat(driver, ":chooser", "[Abrir chooser]")
    time.sleep(2)

    # Selecionar "Lives"
    wait = WebDriverWait(driver, 20)
    select_elem = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "select.form-select.form-select-sm")))
    driver.execute_script("arguments[0].value = 'live'; arguments[0].dispatchEvent(new Event('change', { bubbles: true }));", select_elem)
    time.sleep(2)

    # Procurar usuário
    candidatos = driver.find_elements(By.CSS_SELECTOR, ".rounded.p-1")
    alvo = None
    for c in candidatos:
        if nome_usuario.lower() in c.text.lower():
            alvo = c
            break
    if not alvo:
        log(f"Usuário {nome_usuario} não encontrado no chooser.", Fore.RED)
        return

    alvo.click()
    time.sleep(1)

    # Localizar "Respeitar"
    while True:
        try:
            respeitar_btn = driver.find_element(By.XPATH, "//div[contains(text(),'Respeitar')]")
            respeitar_btn.click()
            time.sleep(1)
        except:
            break
    log(f"Respeitou {nome_usuario}.", Fore.GREEN)

# --- 3. Beijar usuário ---
def beijar_usuario(driver, nome_usuario):
    # Abrir chooser
    enviar_chat(driver, ":chooser", "[Abrir chooser]")
    time.sleep(2)

    # Selecionar "Lives"
    wait = WebDriverWait(driver, 20)
    select_elem = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "select.form-select.form-select-sm")))
    driver.execute_script("arguments[0].value = 'live'; arguments[0].dispatchEvent(new Event('change', { bubbles: true }));", select_elem)
    time.sleep(2)

    # Procurar usuário
    candidatos = driver.find_elements(By.CSS_SELECTOR, ".rounded.p-1")
    alvo = None
    for c in candidatos:
        if nome_usuario.lower() in c.text.lower():
            alvo = c
            break
    if not alvo:
        log(f"Usuário {nome_usuario} não encontrado no chooser.", Fore.RED)
        return

    alvo.click()
    time.sleep(1)

    # Localizar "Beijar"
    while True:
        try:
            beijar_btn = driver.find_element(By.XPATH, "//div[contains(text(),'Beijar')]")
            beijar_btn.click()
            time.sleep(1.1)
        except:
            break
    log(f"Beijou {nome_usuario}.", Fore.GREEN)
