# -*- coding: utf-8 -*-
"""
Automação para sistema SwissRe de cotação de seguros
"""

import os
import time
import logging
from typing import Dict, Any, Tuple, Optional
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

logger = logging.getLogger(__name__)

class SwissReAutomation:
    """
    Classe para automação do sistema SwissRe
    """
    
    def __init__(self):
        self.login_url = os.getenv('SWISSRE_LOGIN_URL', 'https://sistema.swissre.com/login')
        self.username = os.getenv('SWISSRE_USERNAME')
        self.password = os.getenv('SWISSRE_PASSWORD')
        self.headless = os.getenv('SWISSRE_HEADLESS', 'True').lower() == 'true'
        
        if not self.username or not self.password:
            logger.warning("Credenciais SwissRe não configuradas")
    
    def executar_cotacao(self, dados_animal: Dict[str, Any]) -> Tuple[bool, str, Optional[str]]:
        """
        Executa cotação no sistema SwissRe
        
        Args:
            dados_animal: Dados do animal para cotação
            
        Returns:
            Tupla (sucesso, mensagem, caminho_pdf)
        """
        if not self.username or not self.password:
            return False, "Credenciais SwissRe não configuradas", None
        
        driver = None
        try:
            # Configurar driver
            driver = self._setup_driver()
            
            # Fazer login
            if not self._fazer_login(driver):
                return False, "Erro no login do sistema SwissRe", None
            
            # Navegar para cotação
            if not self._navegar_para_cotacao(driver):
                return False, "Erro ao navegar para página de cotação", None
            
            # Preencher formulário
            if not self._preencher_formulario(driver, dados_animal):
                return False, "Erro ao preencher formulário de cotação", None
            
            # Gerar cotação
            if not self._gerar_cotacao(driver):
                return False, "Erro ao gerar cotação", None
            
            # Baixar PDF
            pdf_path = self._baixar_pdf(driver, dados_animal)
            if not pdf_path:
                return False, "Erro ao baixar PDF da cotação", None
            
            logger.info(f"Cotação gerada com sucesso: {pdf_path}")
            return True, "Cotação gerada com sucesso", pdf_path
            
        except Exception as e:
            logger.error(f"Erro na automação SwissRe: {str(e)}")
            return False, f"Erro na automação: {str(e)}", None
        
        finally:
            if driver:
                try:
                    driver.quit()
                except:
                    pass
    
    def _setup_driver(self) -> webdriver.Chrome:
        """
        Configura e retorna driver do Chrome
        """
        try:
            chrome_options = Options()
            
            if self.headless:
                chrome_options.add_argument('--headless')
            
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920,1080')
            
            # Configurar download
            download_dir = os.path.join(os.getcwd(), 'static_files')
            os.makedirs(download_dir, exist_ok=True)
            
            prefs = {
                "download.default_directory": download_dir,
                "download.prompt_for_download": False,
                "download.directory_upgrade": True,
                "safebrowsing.enabled": True
            }
            chrome_options.add_experimental_option("prefs", prefs)
            
            # Instalar e configurar driver
            driver_path = ChromeDriverManager().install()
            driver = webdriver.Chrome(executable_path=driver_path, options=chrome_options)
            
            driver.implicitly_wait(10)
            
            return driver
            
        except Exception as e:
            logger.error(f"Erro ao configurar driver: {str(e)}")
            raise
    
    def _fazer_login(self, driver: webdriver.Chrome) -> bool:
        """
        Faz login no sistema SwissRe
        """
        try:
            driver.get(self.login_url)
            
            # Aguardar página carregar
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.NAME, "username"))
            )
            
            # Preencher credenciais
            username_field = driver.find_element(By.NAME, "username")
            password_field = driver.find_element(By.NAME, "password")
            
            username_field.clear()
            username_field.send_keys(self.username)
            
            password_field.clear()
            password_field.send_keys(self.password)
            
            # Clicar em login
            login_button = driver.find_element(By.XPATH, "//button[@type='submit']")
            login_button.click()
            
            # Aguardar login
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.CLASS_NAME, "dashboard"))
            )
            
            logger.info("Login realizado com sucesso")
            return True
            
        except Exception as e:
            logger.error(f"Erro no login: {str(e)}")
            return False
    
    def _navegar_para_cotacao(self, driver: webdriver.Chrome) -> bool:
        """
        Navega para página de cotação
        """
        try:
            # Procurar link de cotação
            cotacao_link = WebDriverWait(driver, 20).until(
                EC.element_to_be_clickable((By.LINK_TEXT, "Nova Cotação"))
            )
            cotacao_link.click()
            
            # Aguardar formulário carregar
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.ID, "form-cotacao"))
            )
            
            logger.info("Navegação para cotação realizada")
            return True
            
        except Exception as e:
            logger.error(f"Erro na navegação: {str(e)}")
            return False
    
    def _preencher_formulario(self, driver: webdriver.Chrome, dados: Dict[str, Any]) -> bool:
        """
        Preenche formulário de cotação
        """
        try:
            # Mapeamento de campos
            campos = {
                'nome_animal': 'input[name="nomeAnimal"]',
                'valor_animal': 'input[name="valorAnimal"]',
                'registro_passaporte': 'input[name="registro"]',
                'raca': 'select[name="raca"]',
                'data_nascimento': 'input[name="dataNascimento"]',
                'sexo': 'select[name="sexo"]',
                'utilizacao': 'select[name="utilizacao"]',
                'endereco_cocheira': 'textarea[name="endereco"]'
            }
            
            for campo, selector in campos.items():
                if campo in dados and dados[campo]:
                    try:
                        element = WebDriverWait(driver, 10).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                        )
                        
                        if element.tag_name == 'select':
                            # Para selects, procurar opção correspondente
                            options = element.find_elements(By.TAG_NAME, "option")
                            for option in options:
                                if dados[campo].lower() in option.text.lower():
                                    option.click()
                                    break
                        else:
                            # Para inputs e textareas
                            element.clear()
                            element.send_keys(dados[campo])
                        
                        time.sleep(0.5)  # Pequena pausa entre campos
                        
                    except Exception as e:
                        logger.warning(f"Erro ao preencher campo {campo}: {str(e)}")
                        continue
            
            logger.info("Formulário preenchido com sucesso")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao preencher formulário: {str(e)}")
            return False
    
    def _gerar_cotacao(self, driver: webdriver.Chrome) -> bool:
        """
        Gera cotação
        """
        try:
            # Clicar em gerar cotação
            gerar_button = WebDriverWait(driver, 20).until(
                EC.element_to_be_clickable((By.ID, "btn-gerar-cotacao"))
            )
            gerar_button.click()
            
            # Aguardar processamento
            WebDriverWait(driver, 60).until(
                EC.presence_of_element_located((By.CLASS_NAME, "cotacao-resultado"))
            )
            
            logger.info("Cotação gerada com sucesso")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao gerar cotação: {str(e)}")
            return False
    
    def _baixar_pdf(self, driver: webdriver.Chrome, dados: Dict[str, Any]) -> Optional[str]:
        """
        Baixa PDF da cotação
        """
        try:
            # Procurar botão de download
            download_button = WebDriverWait(driver, 20).until(
                EC.element_to_be_clickable((By.ID, "btn-download-pdf"))
            )
            download_button.click()
            
            # Aguardar download
            time.sleep(5)
            
            # Procurar arquivo baixado
            download_dir = os.path.join(os.getcwd(), 'static_files')
            files = os.listdir(download_dir)
            
            # Procurar PDF mais recente
            pdf_files = [f for f in files if f.endswith('.pdf')]
            if pdf_files:
                # Ordenar por data de modificação
                pdf_files.sort(key=lambda x: os.path.getmtime(os.path.join(download_dir, x)), reverse=True)
                
                # Renomear arquivo
                nome_animal = dados.get('nome_animal', 'animal').replace(' ', '_')
                novo_nome = f"cotacao_{nome_animal}_{int(time.time())}.pdf"
                
                old_path = os.path.join(download_dir, pdf_files[0])
                new_path = os.path.join(download_dir, novo_nome)
                
                os.rename(old_path, new_path)
                
                logger.info(f"PDF baixado: {new_path}")
                return new_path
            
            return None
            
        except Exception as e:
            logger.error(f"Erro ao baixar PDF: {str(e)}")
            return None
    
    def testar_conexao(self) -> bool:
        """
        Testa conexão com o sistema SwissRe
        """
        if not self.username or not self.password:
            return False
        
        driver = None
        try:
            driver = self._setup_driver()
            return self._fazer_login(driver)
        except:
            return False
        finally:
            if driver:
                try:
                    driver.quit()
                except:
                    pass

