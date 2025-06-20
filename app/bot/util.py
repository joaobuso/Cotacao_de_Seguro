import time
import re
import logging
import unicodedata
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains

# Configuração básica do logger
logging.basicConfig(
    level=logging.INFO,  # ou DEBUG, WARNING, ERROR
    format='%(asctime)s [%(levelname)s] %(message)s')

def normalizar(texto):
    # Remove acentuação
    texto = unicodedata.normalize('NFKD', texto)
    texto = texto.encode('ASCII', 'ignore').decode('ASCII')
    # Remove caracteres especiais, mantendo letras, números e espaços
    texto = re.sub(r'[^a-zA-Z0-9\s]', '', texto)
    return texto.lower().strip()

def click_element(driver,
                  xpath_text: str,
                  input_text: str = None,
                  get_text: bool = False,
                  click_selenium: bool = False,
                  click_script: bool = False,
                  timeout=2,
                  max_tentativas=3,
                  selector_type: str = 'xpath',
                  move_to_element: str = None):

    tentativa = 1
    element = None

    by_type = {
        'id': By.ID,
        'xpath': By.XPATH,
        'css': By.CSS_SELECTOR,
        'name': By.NAME,
        'class': By.CLASS_NAME,
        'link_text': By.LINK_TEXT,
        'partial_link_text': By.PARTIAL_LINK_TEXT,
        'tag': By.TAG_NAME
    }.get(selector_type.lower(), By.XPATH)

    while tentativa <= max_tentativas:
        time.sleep(1)
        try:

            # Tenta localizar fora de iframes
            try:
                element = WebDriverWait(driver, timeout).until(
                    EC.presence_of_element_located((by_type, xpath_text))
                )

            except Exception:
                # Tenta localizar dentro de iframes
                iframes = driver.find_elements(By.TAG_NAME, "iframe")
                for index, iframe in enumerate(iframes):
                    try:
                        driver.switch_to.frame(iframe)
                        element = WebDriverWait(driver, timeout).until(
                            EC.presence_of_element_located((by_type,
                                                                xpath_text))
                        )

                        break
                    except Exception:
                        driver.switch_to.default_content()

            if element is None:
                raise Exception("Elemento não encontrado")

            # Ação Click
            if move_to_element:
                ActionChains(driver).move_to_element(element).perform()
            if click_selenium:
                element.click()
            elif click_script:
                # Clicar via JavaScript
                driver.execute_script("arguments[0].scrollIntoView(true);",
                                        element)
                driver.execute_script("arguments[0].click();",
                                        element)

            # Inserir texto se necessário
            if input_text:
                element.clear()
                element.send_keys(input_text)
                # Pressionar TAB
                element.send_keys(Keys.TAB)
                logging.info(f"Texto '{input_text}' inserido com sucesso.")

            if get_text:
                element.text
                return element.text

            return element

        except Exception:
            tentativa += 1
            time.sleep(1)
            driver.switch_to.default_content()

    logging.error(f"[{xpath_text}] Falha após {max_tentativas} tentativas.")
    return False