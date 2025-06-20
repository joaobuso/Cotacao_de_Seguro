import time
import pyotp
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from util import *

# Configuração básica do logger
logging.basicConfig(
    level=logging.INFO,  # ou DEBUG, WARNING, ERROR
    format='%(asctime)s [%(levelname)s] %(message)s')

def login_swissre(max_tentativas=4):
    tentativa = 0
    driver = None
    # Initializing the browser using webdriver-manager
    logging.info("Início etapa login")
    # Configurar opções do Chrome
    options = Options()
    options.add_argument("--start-maximized")  # ou outros argumentos como --headless, etc.
    options.add_argument("--incognito") 

    # Usar o ChromeDriver automático
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

    # Accessing the URL
    driver.maximize_window()
    driver.get('https://corsobr.swissre.com/corsobr#')

    while tentativa < max_tentativas:
        tentativa += 1
        logging.info(f"Tentativa {tentativa} de login no swissre")

        try:
            # Waiting a few seconds to view the loaded page (optional)
            driver.implicitly_wait(5)

            # Entering the username:
            click_element(driver=driver, xpath_text="identifier", selector_type="name", input_text='equinosseguros@gmail.com')
            #driver.find_element(By.NAME, 'identifier').send_keys('equinosseguros@gmail.com')

            # Click Proximo
            click_element(driver=driver, xpath_text="//input[@type='submit' and @value='Próximo']", click_selenium=True)

            # Entering the password:
            click_element(driver=driver, xpath_text="credentials.passcode", selector_type="name", input_text='Framar1979$2025')

            # Click Verificar
            click_element(driver=driver, xpath_text="//input[@type='submit' and @value='Verificar']", click_selenium=True)

            # Geração do código
            totp = pyotp.TOTP("BX35M55BRLO3UIYM")
            codigo = totp.now()
            # Aguarde o carregamento do campo e preencha o código
            time.sleep(2)
            # Inserir Codigo Token
            click_element(driver=driver, xpath_text="credentials.passcode", selector_type="name", input_text=codigo)

            # Click Verificar
            click_element(driver=driver, xpath_text="//input[@type='submit' and @value='Verificar']", click_selenium=True)

            try:
                # Esperar o label estar clicável e clicar nele
                label = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, "//label[@for='ckbAcceptTerm']")))
                label.click()
                click_element(driver=driver, xpath_text="btnAcceptSend", selector_type="id", click_selenium=True)
            except Exception as e:
                e = e

            try:
                el = driver.find_element(By.XPATH, "(//button[contains(@class, 'wm-visual-design-button')])[last()]")
                driver.execute_script("arguments[0].click();", el)
                el = driver.find_element(By.XPATH, "(//button[contains(@class, 'wm-visual-design-button')])[last()]")
                driver.execute_script("arguments[0].click();", el)
            except Exception as e:
                e = e

            validacao_login = click_element(driver=driver, xpath_text="//i[@class='fa fa-bars']", selector_type="xpath", timeout=1, max_tentativas=1)
            if not validacao_login:
                # Esperar o label estar clicável e clicar nele
                label = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, "//input[@id='removePreviousAuthentication']")))
                label.click()
                click_element(driver=driver, xpath_text="btnLogin", selector_type="id", click_selenium=True)
                continue

            # Waiting a few seconds to verify the page has loaded (optional)
            WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.XPATH, "//i[@class='fa fa-bars']")))
            logging.info("Login realizado com sucesso")
            return driver

        except Exception as e:
            logging.warning(f"Erro na tentativa {tentativa}: {str(e)}")
            if driver:
                driver.quit()

            # Aguarda um pouco antes de tentar de novo
            time.sleep(2)

    logging.error("Falha ao realizar login após 3 tentativas.")
    raise Exception("Não foi possível realizar login no swissre.")
 

driver = login_swissre()

# click Menu
click_element(driver=driver, xpath_text="//i[@class='fa fa-bars']", selector_type="xpath", click_selenium=True)

# CLick Emissão
click_element(driver=driver, xpath_text="//label[@for='group-5' and contains(., 'Emissão')]", selector_type="xpath", click_selenium=True)

# Click Cotação
click_element(driver=driver, xpath_text="//a[@id='0260_HeaderMenu' and text()='Cotação']", selector_type="xpath", click_selenium=True)

# Click Selecione
click_element(driver=driver, xpath_text="//span[text()='Selecione']", selector_type="xpath", click_selenium=True)

# Click Tipo cotação
click_element(driver=driver, xpath_text="//li[a[contains(text(), '64014 - Animal - Equinos')]]", selector_type="xpath", click_selenium=True)

# Click Salvar e Continuar
click_element(driver=driver, xpath_text="save", selector_type="id", click_selenium=True, timeout=15)

# Inserir CPF/CNPJ Segurado
time.sleep(7)
click_element(driver=driver, xpath_text="//input[@ng-model='issuanceData.ContractData.InsuredDocumentNumber']", input_text='54.488.079/0001-70', timeout=15)

# Inserir CPF/CNPJ Beneficiario
time.sleep(5)
click_element(driver=driver, xpath_text="//input[@ng-model='issuanceData.ContractData.BeneficiaryDocumentNumber']", input_text='54.488.079/0001-70', timeout=15)

# Click SUC-CPD
click_element(driver=driver, xpath_text="txtBrokerCpdCode", selector_type="id", click_selenium=True)

# Selcionar SUC-CPD
click_element(driver=driver, xpath_text="//a[normalize-space(text())='635-544270']", click_selenium=True)

# Click Agencia Produtora
click_element(driver=driver, xpath_text="//input[contains(@class, 'form-control') and contains(@class, 'ng-scope')]", input_text='0000')

agencia_produtora = click_element(driver=driver, xpath_text="//input[@ng-model='issuanceData.IssuanceOvIntegration.AccountNumber']", click_selenium=True)
# Simula Shift + Tab para voltar ao campo anterior e digita "0000"
actions = ActionChains(driver)
actions.key_down(Keys.SHIFT).send_keys(Keys.TAB).key_up(Keys.SHIFT).send_keys("0000").perform()
click_element(driver=driver, xpath_text="//div[@class='media-body' and contains(., '0000') and contains(., 'Sem Agência')]", click_selenium=True)

# Click Salvar e Continuar
click_element(driver=driver, xpath_text="//button[@ng-click='performAccordion(2, 3, false)']", selector_type='xpath', click_script=True)

# Adicionar Novo Item
time.sleep(4)
click_element(driver=driver, xpath_text="lnkAddItemDataModal", selector_type='id', click_script=True)

# Inserir Nome
click_element(driver=driver, xpath_text="txtend_nomris", selector_type='id', input_text='AGHATA SMARVEL CHEX')

# Inserir Registro
click_element(driver=driver, xpath_text="txtend_identris", selector_type='id', input_text='P268589')

# Inserir Data Nascimento
click_element(driver=driver, xpath_text="datend_dataris", selector_type='id', input_text='06082017')

# Inserir Utilização
click_element(driver=driver, xpath_text="//*[@id='nyacod_ocup']/button", click_selenium=True)
click_element(driver=driver, xpath_text="//*[@id='nyacod_ocup']/div/div/input", selector_type='xpath', input_text='49 - Reprodução')
click_element(driver=driver, xpath_text="//a[contains(text(), '49 - Reprodução')]", click_selenium=True)

# Inserir Raça
click_element(driver=driver, xpath_text="//*[@id='nyacod_enqdr']/button", click_selenium=True)
click_element(driver=driver, xpath_text="//*[@id='nyacod_enqdr']/div/div/input", selector_type='xpath', input_text='1022 - Quarto de Milha')
click_element(driver=driver, xpath_text="//a[contains(text(), '1022 - Quarto de Milha')]", click_selenium=True)

# Inserir Sexo
click_element(driver=driver, xpath_text="//*[@id='nyacod_categ']/button", click_selenium=True)
click_element(driver=driver, xpath_text="//*[@id='nyacod_categ']/div/div/input", selector_type='xpath', input_text='2 - Fêmea')
click_element(driver=driver, xpath_text="//a[contains(text(), '2 - Fêmea')]", click_selenium=True)

# Inserir PLano
click_element(driver=driver, xpath_text="//*[@id='nyacod_plano']/button", click_selenium=True)
click_element(driver=driver, xpath_text="//*[@id='nyacod_plano']/div/div/input", selector_type='xpath', input_text='99999 - Padrão')
click_element(driver=driver, xpath_text="//a[contains(text(), '99999 - Padrão')]", click_selenium=True)

# Inserir Afinidade
click_element(driver=driver, xpath_text="//*[@id='nyacod_afinidade']/button", click_selenium=True)
click_element(driver=driver, xpath_text="//*[@id='nyacod_afinidade']/div/div/input", selector_type='xpath', input_text='26 - Padrão')
click_element(driver=driver, xpath_text="//a[contains(text(), '26 - Padrão')]", click_selenium=True)

# Inserir Cep
click_element(driver=driver, xpath_text="cep", selector_type='id', input_text='76280000')

# Inserir Logradouro
click_element(driver=driver, xpath_text="address", selector_type='id', input_text='SITIO')

# Inserir Numero
click_element(driver=driver, xpath_text="numberofaddress", selector_type='id', input_text='1')

# Inserir Bairro
click_element(driver=driver, xpath_text="district", selector_type='id', input_text='ZONA RURAL')

# Inserir Salvar
click_element(driver=driver, xpath_text="btnSaveItemDataModal", selector_type='id', click_script=True)

print('feito')




