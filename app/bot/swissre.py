import time
import pyotp
import logging
import os
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager
from .util import *

# Configuração básica do logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)

class SwissReCotador:
    """
    Classe para automatizar cotações no site da Swiss Re.
    """
    
    def __init__(self):
        self.driver = None
        self.logged_in = False
    
    def setup_driver(self):
        """Configura e inicializa o driver do Chrome."""
        try:
            options = Options()
            options.add_argument("--start-maximized")
            options.add_argument("--incognito")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            
            # Para ambiente de produção, adicionar headless
            # options.add_argument("--headless")
            
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=options)
            self.driver.maximize_window()
            return True
        except Exception as e:
            logging.error(f"Erro ao configurar driver: {e}")
            return False
    
    def login_swissre(self, max_tentativas=3):
        """Realiza login no site da Swiss Re."""
        if not self.driver:
            if not self.setup_driver():
                return False
        
        tentativa = 0
        
        while tentativa < max_tentativas:
            tentativa += 1
            logging.info(f"Tentativa {tentativa} de login no SwissRe")
            
            try:
                # Acessar o site
                self.driver.get('https://corsobr.swissre.com/corsobr#')
                self.driver.implicitly_wait(5)
                
                # Inserir email
                email_field = self.driver.find_element(By.NAME, 'identifier')
                email_field.clear()
                email_field.send_keys('equinosseguros@gmail.com')
                
                # Clicar em Próximo
                next_button = self.driver.find_element(By.XPATH, "//input[@type='submit' and @value='Próximo']")
                next_button.click()
                
                # Inserir senha
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.NAME, "credentials.passcode"))
                )
                password_field = self.driver.find_element(By.NAME, 'credentials.passcode')
                password_field.clear()
                password_field.send_keys('Framar1979$2025')
                
                # Clicar em Verificar
                verify_button = self.driver.find_element(By.XPATH, "//input[@type='submit' and @value='Verificar']")
                verify_button.click()
                
                # Gerar e inserir código TOTP
                totp = pyotp.TOTP("BX35M55BRLO3UIYM")
                codigo = totp.now()
                
                time.sleep(2)
                totp_field = self.driver.find_element(By.NAME, 'credentials.passcode')
                totp_field.clear()
                totp_field.send_keys(codigo)
                
                # Clicar em Verificar novamente
                verify_button = self.driver.find_element(By.XPATH, "//input[@type='submit' and @value='Verificar']")
                verify_button.click()
                
                # Lidar com termos de aceite se aparecerem
                try:
                    label = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, "//label[@for='ckbAcceptTerm']"))
                    )
                    label.click()
                    accept_button = self.driver.find_element(By.ID, "btnAcceptSend")
                    accept_button.click()
                except:
                    pass
                
                # Lidar com botões de design visual se aparecerem
                try:
                    buttons = self.driver.find_elements(By.XPATH, "//button[contains(@class, 'wm-visual-design-button')]")
                    for button in buttons[-2:]:  # Clicar nos últimos 2 botões
                        self.driver.execute_script("arguments[0].click();", button)
                        time.sleep(1)
                except:
                    pass
                
                # Verificar se o login foi bem-sucedido
                try:
                    WebDriverWait(self.driver, 10).until(
                        EC.visibility_of_element_located((By.XPATH, "//i[@class='fa fa-bars']"))
                    )
                    logging.info("Login realizado com sucesso")
                    self.logged_in = True
                    return True
                except:
                    # Tentar lidar com autenticação anterior
                    try:
                        remove_auth = self.driver.find_element(By.ID, 'removePreviousAuthentication')
                        remove_auth.click()
                        login_button = self.driver.find_element(By.ID, "btnLogin")
                        login_button.click()
                        continue
                    except:
                        pass
                
            except Exception as e:
                logging.warning(f"Erro na tentativa {tentativa}: {str(e)}")
                time.sleep(2)
        
        logging.error("Falha ao realizar login após todas as tentativas.")
        return False
    
    def navegar_para_cotacao(self):
        """Navega para a seção de cotação."""
        try:
            if not self.logged_in:
                return False
            
            # Clicar no menu
            menu_button = self.driver.find_element(By.XPATH, "//i[@class='fa fa-bars']")
            menu_button.click()
            time.sleep(1)
            
            # Clicar em Emissão
            emissao_button = self.driver.find_element(By.XPATH, "//label[@for='group-5' and contains(., 'Emissão')]")
            emissao_button.click()
            time.sleep(1)
            
            # Clicar em Cotação
            cotacao_button = self.driver.find_element(By.XPATH, "//a[@id='0260_HeaderMenu' and text()='Cotação']")
            cotacao_button.click()
            time.sleep(2)
            
            return True
        except Exception as e:
            logging.error(f"Erro ao navegar para cotação: {e}")
            return False
    
    def selecionar_tipo_cotacao(self):
        """Seleciona o tipo de cotação para equinos."""
        try:
            # Clicar em Selecione
            select_button = self.driver.find_element(By.XPATH, "//span[text()='Selecione']")
            select_button.click()
            time.sleep(1)
            
            # Selecionar tipo de cotação para equinos
            equinos_option = self.driver.find_element(By.XPATH, "//li[a[contains(text(), '64014 - Animal - Equinos')]]")
            equinos_option.click()
            time.sleep(1)
            
            # Salvar e continuar
            save_button = self.driver.find_element(By.ID, "save")
            save_button.click()
            
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.XPATH, "//input[@ng-model='issuanceData.ContractData.InsuredDocumentNumber']"))
            )
            
            return True
        except Exception as e:
            logging.error(f"Erro ao selecionar tipo de cotação: {e}")
            return False
    
    def preencher_dados_contratuais(self):
        """Preenche os dados contratuais básicos."""
        try:
            time.sleep(3)
            
            # Inserir CPF/CNPJ Segurado
            segurado_field = self.driver.find_element(By.XPATH, "//input[@ng-model='issuanceData.ContractData.InsuredDocumentNumber']")
            segurado_field.clear()
            segurado_field.send_keys('54.488.079/0001-70')
            time.sleep(1)
            
            # Inserir CPF/CNPJ Beneficiário
            beneficiario_field = self.driver.find_element(By.XPATH, "//input[@ng-model='issuanceData.ContractData.BeneficiaryDocumentNumber']")
            beneficiario_field.clear()
            beneficiario_field.send_keys('54.488.079/0001-70')
            time.sleep(1)
            
            # Selecionar SUC-CPD
            suc_cpd_button = self.driver.find_element(By.ID, "txtBrokerCpdCode")
            suc_cpd_button.click()
            time.sleep(1)
            
            suc_cpd_option = self.driver.find_element(By.XPATH, "//a[normalize-space(text())='635-544270']")
            suc_cpd_option.click()
            time.sleep(1)
            
            # Preencher Agência Produtora
            actions = ActionChains(self.driver)
            actions.key_down(Keys.SHIFT).send_keys(Keys.TAB).key_up(Keys.SHIFT).send_keys("0000").perform()
            time.sleep(1)
            
            agencia_option = self.driver.find_element(By.XPATH, "//div[@class='media-body' and contains(., '0000') and contains(., 'Sem Agência')]")
            agencia_option.click()
            time.sleep(1)
            
            # Salvar e continuar para próxima etapa
            continue_button = self.driver.find_element(By.XPATH, "//button[@ng-click='performAccordion(2, 3, false)']")
            self.driver.execute_script("arguments[0].click();", continue_button)
            time.sleep(3)
            
            return True
        except Exception as e:
            logging.error(f"Erro ao preencher dados contratuais: {e}")
            return False
    
    def adicionar_item_animal(self, dados_animal):
        """Adiciona um item de animal com os dados fornecidos."""
        try:
            # Clicar em Adicionar Novo Item
            add_item_button = self.driver.find_element(By.ID, "lnkAddItemDataModal")
            self.driver.execute_script("arguments[0].click();", add_item_button)
            time.sleep(2)
            
            # Preencher nome do animal
            nome_field = self.driver.find_element(By.ID, "txtend_nomris")
            nome_field.clear()
            nome_field.send_keys(dados_animal['nome_animal'])
            
            # Preencher registro
            registro_field = self.driver.find_element(By.ID, "txtend_identris")
            registro_field.clear()
            registro_field.send_keys(dados_animal['registro_passaporte'])
            
            # Preencher data de nascimento (formato DDMMAAAA)
            data_nascimento = dados_animal['data_nascimento'].replace('/', '')
            data_field = self.driver.find_element(By.ID, "datend_dataris")
            data_field.clear()
            data_field.send_keys(data_nascimento)
            
            # Selecionar utilização
            self._selecionar_dropdown("nyacod_ocup", "49 - Reprodução")
            
            # Selecionar raça
            self._selecionar_dropdown("nyacod_enqdr", "1022 - Quarto de Milha")
            
            # Selecionar sexo
            sexo_map = {
                'fêmea': '2 - Fêmea',
                'femea': '2 - Fêmea',
                'inteiro': '1 - Inteiro',
                'castrado': '3 - Castrado'
            }
            sexo_option = sexo_map.get(dados_animal['sexo'].lower(), '2 - Fêmea')
            self._selecionar_dropdown("nyacod_categ", sexo_option)
            
            # Selecionar plano
            self._selecionar_dropdown("nyacod_plano", "99999 - Padrão")
            
            # Selecionar afinidade
            self._selecionar_dropdown("nyacod_afinidade", "26 - Padrão")
            
            # Preencher endereço (extrair CEP se possível)
            endereco = dados_animal['endereco_cocheira']
            cep = self._extrair_cep(endereco)
            
            cep_field = self.driver.find_element(By.ID, "cep")
            cep_field.clear()
            cep_field.send_keys(cep or "76280000")  # CEP padrão se não encontrar
            
            # Preencher outros campos de endereço
            address_field = self.driver.find_element(By.ID, "address")
            address_field.clear()
            address_field.send_keys("SITIO")
            
            number_field = self.driver.find_element(By.ID, "numberofaddress")
            number_field.clear()
            number_field.send_keys("1")
            
            district_field = self.driver.find_element(By.ID, "district")
            district_field.clear()
            district_field.send_keys("ZONA RURAL")
            
            # Salvar item
            save_item_button = self.driver.find_element(By.ID, "btnSaveItemDataModal")
            self.driver.execute_script("arguments[0].click();", save_item_button)
            time.sleep(3)
            
            return True
        except Exception as e:
            logging.error(f"Erro ao adicionar item do animal: {e}")
            return False
    
    def _selecionar_dropdown(self, dropdown_id, opcao_texto):
        """Método auxiliar para selecionar opções em dropdowns."""
        try:
            # Clicar no dropdown
            dropdown_button = self.driver.find_element(By.XPATH, f"//*[@id='{dropdown_id}']/button")
            dropdown_button.click()
            time.sleep(1)
            
            # Digitar no campo de busca
            search_field = self.driver.find_element(By.XPATH, f"//*[@id='{dropdown_id}']/div/div/input")
            search_field.clear()
            search_field.send_keys(opcao_texto)
            time.sleep(1)
            
            # Selecionar a opção
            option = self.driver.find_element(By.XPATH, f"//a[contains(text(), '{opcao_texto}')]")
            option.click()
            time.sleep(1)
        except Exception as e:
            logging.warning(f"Erro ao selecionar dropdown {dropdown_id}: {e}")
    
    def _extrair_cep(self, endereco):
        """Extrai CEP do endereço se possível."""
        import re
        cep_pattern = r'(\d{5}-?\d{3})'
        match = re.search(cep_pattern, endereco)
        if match:
            return match.group(1).replace('-', '')
        return None
    
    def gerar_cotacao(self, dados_animal):
        """Processo completo de geração de cotação."""
        try:
            logging.info("Iniciando processo de cotação")
            
            # Fazer login
            if not self.login_swissre():
                return False, "Erro no login"
            
            # Navegar para cotação
            if not self.navegar_para_cotacao():
                return False, "Erro ao navegar para cotação"
            
            # Selecionar tipo de cotação
            if not self.selecionar_tipo_cotacao():
                return False, "Erro ao selecionar tipo de cotação"
            
            # Preencher dados contratuais
            if not self.preencher_dados_contratuais():
                return False, "Erro ao preencher dados contratuais"
            
            # Adicionar item do animal
            if not self.adicionar_item_animal(dados_animal):
                return False, "Erro ao adicionar dados do animal"
            
            # Aqui você pode adicionar mais etapas para finalizar a cotação
            # e gerar o PDF
            
            logging.info("Cotação gerada com sucesso")
            return True, "Cotação gerada com sucesso"
            
        except Exception as e:
            logging.error(f"Erro no processo de cotação: {e}")
            return False, f"Erro no processo: {str(e)}"
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Limpa recursos e fecha o driver."""
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
            self.driver = None
            self.logged_in = False

def executar_cotacao_swissre(dados_animal):
    """
    Função principal para executar cotação no SwissRe.
    
    Args:
        dados_animal (dict): Dicionário com os dados do animal
        
    Returns:
        tuple: (sucesso, mensagem, caminho_pdf)
    """
    cotador = SwissReCotador()
    sucesso, mensagem = cotador.gerar_cotacao(dados_animal)
    
    # Por enquanto, retornamos None para o PDF
    # Você pode implementar a lógica para salvar/baixar o PDF aqui
    caminho_pdf = None
    
    return sucesso, mensagem, caminho_pdf

