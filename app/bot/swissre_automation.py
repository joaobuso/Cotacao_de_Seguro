# -*- coding: utf-8 -*-
"""
Módulo de Automação SwissRe - Exemplo de Implementação
"""

import os
import json
import time
import logging
import requests
from openai import OpenAI
from dotenv import load_dotenv
from datetime import datetime
logger = logging.getLogger(__name__)

# Carrega as variáveis definidas no arquivo .env
load_dotenv()


path_bot = os.path.dirname(os.path.abspath(__file__))
path_bot_download = os.path.join(path_bot, 'download')
# Cria diretório temporário (persistirá enquanto o container estiver rodando)
os.makedirs(path_bot_download, exist_ok=True)

# Credenciais
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TOKEN_URL = "https://identity.swissre.com/oauth2/ausesyclwtVLbaoLc0i7/v1/token"
API_URL = "https://corsobr.api.swissre.com/issuance/v1/CreateQuotation"
API_URL_DOCUMENT = 'https://corsobr.api.swissre.com/document/v1/PrintDocument'




def normalizar_retorno_json(dados):
    """
    Normaliza a resposta:
    - Se for lista com 1 item, retorna o dicionário interno.
    - Se for lista com vários, retorna a lista original.
    - Se já for dicionário, retorna direto.
    """
    if isinstance(dados, list):
        if len(dados) == 1 and isinstance(dados[0], dict):
            return dados[0]
        else:
            return dados
    elif isinstance(dados, dict):
        return dados
    else:
        raise ValueError("Formato inesperado de dados retornados.")

def extrair_dados_chatgpt(prompt: str, max_tentativas: int = 6, delay_retry: int = 4):
    """
    Envia um texto (prompt) para a API do ChatGPT e tenta extrair um JSON válido e completo.
    Faz múltiplas tentativas se necessário.
    Também valida se todas as chaves obrigatórias estão presentes e preenchidas.

    Returns:
        dict | bool: Dicionário com dados normalizados ou False em caso de falha.
    """
    # ✅ Lista de chaves obrigatórias
    chaves_obrigatorias = [
        "cep",
        "rua",
        "numero",
        "bairro",
        "uf",
        "cidade",
        "valor",
        "nome",
        "cpf"
    ]
    # Inicializa cliente da OpenAI
    client = OpenAI(api_key=OPENAI_API_KEY)
    for tentativa in range(1, max_tentativas + 1):
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Responda sempre em JSON puro."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0
            )

            dados_brutos = response.choices[0].message.content.strip()

            dados_limpos = (
                dados_brutos
                .removeprefix("```json")
                .removesuffix("```")
                .strip()
            )

            json_dados = json.loads(dados_limpos)
            dados = normalizar_retorno_json(json_dados)

            if not isinstance(dados, dict):
                raise Exception("Formato inesperado: JSON não é um dicionário.")

            # ✅ Verifica se todas as chaves obrigatórias estão presentes
            chaves_presentes = set(dados.keys())
            chaves_faltantes = [k for k in chaves_obrigatorias if k not in chaves_presentes]

            if chaves_faltantes:
                raise Exception(f"Chaves obrigatórias ausentes: {', '.join(chaves_faltantes)}")

            # ✅ Verifica se todos os valores obrigatórios estão preenchidos (não vazios)
            todos_os_valores_nao_vazios = all(
                dados.get(k) not in (None, "", []) for k in chaves_obrigatorias
            )

            if not todos_os_valores_nao_vazios:
                chaves_vazias = [k for k in chaves_obrigatorias if not dados.get(k)]
                raise Exception(f"Alguns valores estão vazios: {', '.join(chaves_vazias)}")

            # ✅ Se passou em todas as validações
            return dados

        except Exception as e:
            print(f"❌ Erro na tentativa {tentativa}: {e}")
            if tentativa < max_tentativas:
                print(f"⏳ Tentando novamente em {delay_retry}s...")
                time.sleep(delay_retry)
            else:
                print("❌ Limite de tentativas atingido.")
                return False

def generate_quotation_pdf(client_data):
  logger.info("Incicio Fluxo de Cotação SwissRe")
  client_data = """
  Nome do Animal: Mancha
  Valor do Animal: 50.000,00
  Numero de Registro: 12345
  Raca: Mangalarga
  Data de Nascimento - 19/06/1985
  Sexo - inteiro
  Utilizacao - lazer
  Endereco: Rua Braulio Mendes Nogueira, 200 Bairro Chacara Recanto Colina Verde
  Cidade: Campinas
  CEP: 13058-831
  Estado SP
  Nome do responsável: Nelson Luiz do Rego Neto
  CPF: 07963557000258"""

  prompt = f"""
  Nome:
  Conversão de dados de texto em dados categorizados em formato de json.

  Descrição:
  De acordo com os dados enviados, Extraia as seguintes informações do Texto do documento e retorne apenas o Json sem texto adicional na resposta no formato JSON com apenas 1 valor tipo string por chave referente as chaves 'cep', 'rua', 'numero', 'bairro', 'uf', 'cidade', 'valor', 'nome' e 'cpf'.

  Instruções:
  Considerar os critérios de captura de dados de cada chave do json conforme detalhado abaixo:
  cep = Cep do endereço fornecido.
  rua = rua do endereço fornecido.
  numero = numero do endereço fornecido.
  bairro = bairro do endereço fornecido.
  uf = unidade de federação do estado.
  cidade = Cidade.
  valor = Valor do animal a ser cotado o seguro.
  nome = Nome do solicitante.
  cpf = CPF do solicitante contendo apenas numeros

  Regras
  - Caso o CEP esteja presente e o endereço esteja faltando, utilize o CEP para preencher automaticamente o endereço completo (logradouro, bairro, cidade, estado).
  - Se algum campo não for encontrado e não puder ser deduzido, deixe vazio.

  Texto: {client_data}
  """

  try:
    resultado = extrair_dados_chatgpt(prompt)
    payload = {
      "productId": "64014",
      "entityTypeId": "SE",
      "endorsementTypeId": "1",
      "calculationTypeId": "AN",
      "startDate": datetime.now().strftime('%Y-%m-%d'),
      "expireDate": "2026-05-07",
      "exemptionTypeId": "1",
      "hasFederalSubsidy": False,
      "hasStateSubsidy": False,
      "hasMunicipalSubsidy": False,
      "currencyId": "1",
      "surveyor": None,
      "policyholder": None,
      "insured": {
        "name": resultado['nome'],
        "documentId": resultado['cpf']
      },
      "beneficiary": {
            "beneficiaryName": resultado['nome'],
            "cpfNumber": resultado['cpf']
        },
      "brokers": [
        {
          "id": "0279651",
          "comission": "10.00"
        }
      ],
      "salesOrganization": {
        "brokerId": "635544270",
        "agencyId": "919",
        "accountNumber": "9879797",
        "postServiceId": "0000"
      },
      "items": [
        {
          "discountAndAggrave": "0",
          "dynamicFields": [
            {
              "id": "cod_item",
              "value": "1"
            },
            {
              "id": "end_nomris",
              "value": "Pocoto SoapUI"
            },
            {
              "id": "end_identris",
              "value": "Pocoto SoapUI"
            },
            {
              "id": "end_dataris",
              "value": "2015-01-01"
            },
            {
              "id": "end_tpenq",
              "value": "45"
            },
            {
              "id": "end_classenq",
              "value": "1003"
            },
            {
              "id": "cod_afinidade",
              "value": "26"
            },
            {
              "id": "end_tplocal",
              "value": "2"
            },
            {
              "id": "cod_reg_agrup",
              "value": "24"
            },
            {
              "id": "cod_reg",
              "value": "241"
            },
            {
              "id": "cod_plano",
              "value": "00107"
            }
          ],
          "coverages": [
            {
              "id": "00003",
              "insuredValue": resultado['valor'],
              "PctFranchise": "0"
            },
            {
              "id": "00438",
              "insuredValue": "100.00",
              "PctFranchise": "10",
              "EffectiveDate": "2021-01-01"
            }
          ],
          "riskArea": {
            "cep": resultado['cep'],
            "address": resultado['rua'],
            "numberOfAddress": resultado['numero'],
            "complement": None,
            "district": resultado['bairro'],
            "unitFederated": resultado['uf'],
            "city": resultado['cidade']
          },
          "clauseDetails": [
            {
              "id": "00103",
              "description": "Desconto Agrupamento - 03%"
            }
          ]
        }
      ]
    }
    logger.info("Capturar Token")
    # 1. Obter token
    data = {
        "grant_type": "client_credentials",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET
    }
    response = requests.post(TOKEN_URL, data=data)
    token = response.json()["access_token"]


    # 2. Montar cabeçalhos
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    # 4. Enviar requisição de cotação
    logger.info("Envio requisição para formalizar cotacao")
    quotation_response = requests.post(API_URL, headers=headers, json=payload)

    dados = quotation_response.json()
    contractNumber = dados['Response']['contractNumber']
    issuanceId = dados['Response']['issuanceId']
    logger.info("Status Code:", quotation_response.status_code)
    logger.info("Response:", quotation_response.json())


    # Capturar Documento .pdf
    payload_doc = {
        "typeId": "1",  # verifique qual typeId corresponde a Proposta/Apólice
        "issuanceId": issuanceId,
        "contractNumber": contractNumber,
        "proposalNumber": ""
    }

    logger.info(f"Cotacao gerada {contractNumber}")
    response_doc = requests.post(API_URL_DOCUMENT, headers=headers, json=payload_doc)

    logger.info("Status Code:", response_doc.status_code)

    path_file = os.path.join(path_bot_download, f"Cotacao_{contractNumber}.pdf")
    if response_doc.status_code == 200:
        # Salvar o PDF em disco
        with open(path_file, "wb") as f:
            f.write(response_doc.content)
        logger.info("Documento salvo como documento.pdf")
        return {
            'success': True,
            'pdf_url': 'pdf_url',
            'pdf_path': path_file,
            'message': 'Cotação gerada com sucesso',
            'quotation_number': contractNumber,
        }
    else:
        logger.info("Erro:", response_doc.text)
        return {
            'success': False,
            'pdf_url': 'pdf_url',
            'pdf_path': 'path_file',
            'message': 'Cotação gerada com sucesso',
            'quotation_number': '',
        }


  except Exception as e:
      logger.error(f"❌ Erro na automação SwissRe: {str(e)}")
      return {
          'success': False,
          'message': f'Erro na automação: {str(e)}'
          }


