# -*- coding: utf-8 -*-
"""
Módulo de Automação SwissRe - Exemplo de Implementação
"""

import os
import re
import json
import time
import calendar
import logging
import requests
from openai import OpenAI
from dotenv import load_dotenv

from datetime import datetime, timedelta, date

from app.bot.pdf_storage import salvar_pdf_mongo
from app.bot.dados_estados import DADOS_ESTADOS

logger = logging.getLogger(__name__)
# Carrega as variáveis definidas no arquivo .env
load_dotenv()


path_bot = os.path.dirname(os.path.abspath(__file__))
path_bot_download = os.path.join(path_bot, 'download')
# Cria diretório temporário (persistirá enquanto o container estiver rodando)
os.makedirs(path_bot_download, exist_ok=True)

# Credenciais e endpoints técnicos.
# Regras comerciais da cotação devem vir da collection swissre_rules no MongoDB.
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TOKEN_URL = os.getenv(
    "SWISSRE_TOKEN_URL",
    "https://identity.swissre.com/oauth2/ausesyclwtVLbaoLc0i7/v1/token"
)
API_URL = os.getenv(
    "SWISSRE_CREATE_QUOTATION_URL",
    "https://corsobr.api.swissre.com/issuance/v1/CreateQuotation"
)
API_URL_DOCUMENT = os.getenv(
    "SWISSRE_PRINT_DOCUMENT_URL",
    "https://corsobr.api.swissre.com/document/v1/PrintDocument"
)

class SwissReAutomation:
    @staticmethod
    def gerar_documento_com_retry(url, headers, payload, tentativas=4):
        tempos_espera = [10, 20, 40, 60]

        ultimo_erro = None

        for tentativa in range(1, tentativas + 1):
            try:
                logger.info(
                    "Tentando gerar documento SwissRe. Tentativa %s/%s",
                    tentativa,
                    tentativas
                )

                response = requests.post(
                    url,
                    headers=headers,
                    json=payload,
                    timeout=120
                )

                logger.info("Status Code documento: %s", response.status_code)

                if response.status_code == 200:
                    return {
                        "success": True,
                        "response": response
                    }

                # 524, 502, 503, 504 são erros temporários
                if response.status_code in [502, 503, 504, 524]:
                    ultimo_erro = f"Erro temporário ao gerar documento: HTTP {response.status_code}"

                    if tentativa < tentativas:
                        espera = tempos_espera[min(tentativa - 1, len(tempos_espera) - 1)]
                        logger.warning(
                            "%s. Aguardando %s segundos antes de tentar novamente.",
                            ultimo_erro,
                            espera
                        )
                        time.sleep(espera)
                        continue

                # Erro não temporário
                return {
                    "success": False,
                    "error": f"Erro ao gerar documento: HTTP {response.status_code}",
                    "status_code": response.status_code,
                    "body": response.text[:1000]
                }

            except requests.exceptions.Timeout:
                ultimo_erro = "Timeout na requisição de documento"

                if tentativa < tentativas:
                    espera = tempos_espera[min(tentativa - 1, len(tempos_espera) - 1)]
                    logger.warning(
                        "%s. Aguardando %s segundos antes de tentar novamente.",
                        ultimo_erro,
                        espera
                    )
                    time.sleep(espera)
                    continue

            except Exception as e:
                ultimo_erro = str(e)
                logger.exception("Erro inesperado ao gerar documento SwissRe")
                break

        return {
            "success": False,
            "error": ultimo_erro or "Não foi possível gerar documento após tentativas"
        }

    def obter_parametro_geral(rules: dict, chave: str):
        """
        Lê um parâmetro obrigatório da seção general do documento swissre_rules.
        Se o parâmetro não existir no banco, falha de forma explícita para evitar
        fallback escondido no código.
        """
        valor = rules.get("general", {}).get(chave)

        if valor is None or valor == "":
            raise Exception(
                f"Parâmetro obrigatório ausente no banco: swissre_rules.general.{chave}"
            )

        return valor

    def to_int(valor, nome_campo: str) -> int:
        try:
            return int(valor)
        except Exception:
            raise Exception(f"Parâmetro {nome_campo} deve ser inteiro. Valor recebido: {valor}")

    def to_float(valor, nome_campo: str) -> float:
        try:
            return float(valor)
        except Exception:
            raise Exception(f"Parâmetro {nome_campo} deve ser numérico. Valor recebido: {valor}")

    def to_bool(valor) -> bool:
        if isinstance(valor, bool):
            return valor

        if isinstance(valor, str):
            return valor.strip().lower() in ["true", "1", "sim", "s", "yes", "y"]

        return bool(valor)

    def normalizar_lista(valor):
        if valor is None:
            return []

        if isinstance(valor, list):
            return [str(v).strip() for v in valor if str(v).strip()]

        if isinstance(valor, str):
            return [v.strip() for v in valor.split(",") if v.strip()]

        return [str(valor).strip()]

    def normalizar_valor_monetario(valor) -> float:
        if isinstance(valor, (int, float)):
            return float(valor)

        texto = str(valor or "").strip()
        texto = texto.replace("R$", "").replace(" ", "")

        if "," in texto:
            texto = texto.replace(".", "").replace(",", ".")
        else:
            texto = texto.replace(",", "")

        return float(texto)

    def obter_secao_mapeamento(rules: dict, nome_secao: str) -> dict:
        """
        Lê uma seção de mapeamento do MongoDB.

        Aceita tanto formato direto:
        "utilizacoesEquinos": {"tambor": "52"}

        quanto formato com metadados:
        "sexoAnimal": {"termos": {"macho": "1"}, "fallbackCodigo": "2"}
        """
        secao = rules.get(nome_secao)

        if secao is None:
            raise Exception(f"Seção obrigatória ausente no banco: swissre_rules.{nome_secao}")

        if not isinstance(secao, dict):
            raise Exception(f"swissre_rules.{nome_secao} deve ser um objeto/dicionário")

        mapa = (
            secao.get("termos")
            or secao.get("mapeamentos")
            or secao.get("mapa")
        )

        if mapa is None:
            mapa = {
                chave: valor
                for chave, valor in secao.items()
                if chave not in [
                    "fallbackCodigo",
                    "fallbackGrupo",
                    "descricao",
                    "descricoes",
                    "observacao"
                ]
            }

        if not isinstance(mapa, dict):
            raise Exception(f"swissre_rules.{nome_secao} deve possuir um mapa de termos válido")

        return mapa

    def buscar_codigo_por_texto(texto_busca: str, mapa: dict, nome_mapa: str, fallback=None):
        """
        Busca um código em um mapa termo -> código usando texto normalizado.
        Os termos maiores são avaliados primeiro para evitar conflito entre
        termos genéricos e específicos.
        """
        texto = SwissReAutomation.normalizar_texto_busca(texto_busca)

        itens = sorted(
            mapa.items(),
            key=lambda item: len(SwissReAutomation.normalizar_texto_busca(item[0])),
            reverse=True
        )

        for termo, configuracao in itens:
            termo_norm = SwissReAutomation.normalizar_texto_busca(termo)

            if not termo_norm:
                continue

            encontrou = (
                re.search(rf"\b{re.escape(termo_norm)}\b", texto) is not None
                or termo_norm in texto
            )

            if encontrou:
                if isinstance(configuracao, dict):
                    codigo = configuracao.get("codigo") or configuracao.get("valor")
                else:
                    codigo = configuracao

                if codigo is None or codigo == "":
                    raise Exception(
                        f"Termo '{termo}' encontrado em {nome_mapa}, mas está sem código configurado."
                    )

                return str(codigo)

        if fallback is not None and fallback != "":
            return str(fallback)

        return None

    def obter_fallback_codigo(rules: dict, nome_secao: str):
        secao = rules.get(nome_secao, {})

        if isinstance(secao, dict):
            return secao.get("fallbackCodigo")

        return None

    def montar_coverages_por_regras(
    rules: dict,
    product_id: str,
    cod_plano: str,
    codigo_utilizacao: str,
    valor_animal: float
    ):
        """
        Monta as coberturas exclusivamente com base nas regras cadastradas
        no MongoDB em swissre_rules.products / limitesPorUtilizacao /
        franquiasPorUtilizacaoCobertura.
        """
        product_id = str(product_id)
        cod_plano = str(cod_plano)
        codigo_utilizacao = str(codigo_utilizacao)

        try:
            product_rules = rules["products"][product_id]
        except KeyError:
            raise Exception(f"Produto {product_id} não configurado em swissre_rules.products")

        try:
            plano_rules = product_rules["planos"][cod_plano]
        except KeyError:
            raise Exception(
                f"Plano {cod_plano} não configurado para o produto {product_id} "
                f"em swissre_rules.products.{product_id}.planos"
            )

        limite_utilizacao = rules.get("limitesPorUtilizacao", {}).get(codigo_utilizacao)
        coverages = []

        for cov in plano_rules.get("coverages", []):
            coverage_id = str(cov.get("id", "")).strip()
            tipo = str(cov.get("tipo", "")).strip().lower()

            if not coverage_id:
                raise Exception(
                    f"Cobertura sem ID configurada para produto {product_id}, plano {cod_plano}"
                )

            if tipo == "basica":
                insured_value = valor_animal

                aplicar_em = SwissReAutomation.normalizar_lista(
                    limite_utilizacao.get("aplicarEm") if limite_utilizacao else []
                )

                if limite_utilizacao and "basica" in aplicar_em:
                    insured_value = min(
                        valor_animal,
                        SwissReAutomation.to_float(
                            limite_utilizacao.get("valorMaximoBasica"),
                            f"limitesPorUtilizacao.{codigo_utilizacao}.valorMaximoBasica"
                        )
                    )

            elif tipo == "veterinaria":
                insured_value = valor_animal

                if cov.get("valorMaximo") not in [None, ""]:
                    insured_value = min(
                        insured_value,
                        SwissReAutomation.to_float(
                            cov.get("valorMaximo"),
                            f"products.{product_id}.planos.{cod_plano}.coverages.{coverage_id}.valorMaximo"
                        )
                    )

            elif tipo == "fixa":
                insured_value = SwissReAutomation.to_float(
                    cov.get("valorFixo"),
                    f"products.{product_id}.planos.{cod_plano}.coverages.{coverage_id}.valorFixo"
                )

            else:
                raise Exception(
                    f"Tipo de cobertura inválido ou não configurado para {coverage_id}: {tipo}. "
                    f"Use: basica, veterinaria ou fixa."
                )

            if cov.get("valorMinimo") not in [None, ""]:
                insured_value = max(
                    insured_value,
                    SwissReAutomation.to_float(
                        cov.get("valorMinimo"),
                        f"products.{product_id}.planos.{cod_plano}.coverages.{coverage_id}.valorMinimo"
                    )
                )

            chave_franquia = f"{codigo_utilizacao}|{coverage_id}"
            regra_franquia = rules.get("franquiasPorUtilizacaoCobertura", {}).get(chave_franquia)

            if regra_franquia:
                pct_franchise = SwissReAutomation.to_float(
                    regra_franquia.get("pctFranchise"),
                    f"franquiasPorUtilizacaoCobertura.{chave_franquia}.pctFranchise"
                )
            else:
                pct_franchise = SwissReAutomation.to_float(
                    cov.get("pctFranchise", 0),
                    f"products.{product_id}.planos.{cod_plano}.coverages.{coverage_id}.pctFranchise"
                )

            coverages.append({
                "id": coverage_id,
                "insuredValue": float(insured_value),
                "pctFranchise": pct_franchise
            })

        if not coverages:
            raise Exception(f"Nenhuma cobertura configurada para produto {product_id}, plano {cod_plano}")

        return coverages

    def identificar_grupo_asinino_muar(resultado: dict, client_data: dict, rules: dict) -> str:
        """
        Identifica o grupo do produto 64017 usando termos cadastrados no banco:
        swissre_rules.gruposAsininosMuares.
        """

        secao = rules.get("gruposAsininosMuares")
        if not isinstance(secao, dict):
            raise Exception(
                "Seção obrigatória ausente ou inválida no banco: "
                "swissre_rules.gruposAsininosMuares"
            )

        texto = SwissReAutomation.normalizar_texto_busca(
            f"{resultado.get('tipo_animal', '')} "
            f"{resultado.get('raca_animal', '')} "
            f"{client_data}"
        )

        for grupo, termos in secao.items():
            if grupo == "fallbackGrupo":
                continue

            if not isinstance(termos, list):
                continue

            for termo in termos:
                termo_norm = SwissReAutomation.normalizar_texto_busca(termo)
                if termo_norm and (
                    re.search(rf"\b{re.escape(termo_norm)}\b", texto) is not None
                    or termo_norm in texto
                ):
                    return str(grupo)

        fallback = secao.get("fallbackGrupo")
        if not fallback:
            raise Exception(
                "Nenhum grupo asinino/muar identificado e fallbackGrupo não está configurado "
                "em swissre_rules.gruposAsininosMuares."
            )

        return str(fallback)

    def resolver_utilizacao_64017(resultado: dict, client_data: dict, rules: dict) -> dict:
        """
        Resolve a Aptidão/Utilização para produto 64017 - Asininos e Muares
        usando swissre_rules.utilizacoes64017.

        Estrutura esperada:
        "utilizacoes64017": {
            "asininos": {"exposicao": "45", "lazer": "47"},
            "muares": {"exposicao": "60", "lazer": "61"}
        }
        """

        grupo = SwissReAutomation.identificar_grupo_asinino_muar(resultado, client_data, rules)
        utilizacoes = rules.get("utilizacoes64017")

        if not isinstance(utilizacoes, dict):
            raise Exception(
                "Seção obrigatória ausente ou inválida no banco: swissre_rules.utilizacoes64017"
            )

        mapa_grupo = utilizacoes.get(grupo)
        if not isinstance(mapa_grupo, dict):
            return {
                "valido": False,
                "codigo": None,
                "descricao": "",
                "grupo": grupo,
                "mensagem": (
                    f"Não existe mapa de utilização configurado para o grupo {grupo} "
                    f"em swissre_rules.utilizacoes64017."
                )
            }

        texto_busca = f"{resultado.get('utilizacao', '')} {client_data}"
        codigo = SwissReAutomation.buscar_codigo_por_texto(
            texto_busca=texto_busca,
            mapa=mapa_grupo,
            nome_mapa=f"utilizacoes64017.{grupo}"
        )

        if not codigo:
            return {
                "valido": False,
                "codigo": None,
                "descricao": "",
                "grupo": grupo,
                "mensagem": (
                    f"A utilização informada não está mapeada para o produto 64017 "
                    f"no grupo {grupo}."
                )
            }

        descricao = rules.get("idadePorUtilizacao", {}).get(str(codigo), {}).get(
            "descricao",
            str(codigo)
        )

        return {
            "valido": True,
            "codigo": str(codigo),
            "descricao": descricao,
            "grupo": grupo,
            "mensagem": "Utilização válida para produto 64017."
        }

    def resolver_raca_64017(resultado: dict, client_data: dict, rules: dict) -> str:
        """
        Resolve raça para produto 64017 usando swissre_rules.racas64017.
        """

        mapa = SwissReAutomation.obter_secao_mapeamento(rules, "racas64017")
        fallback = SwissReAutomation.obter_fallback_codigo(rules, "racas64017")

        codigo = SwissReAutomation.buscar_codigo_por_texto(
            texto_busca=(
                f"{resultado.get('raca_animal', '')} "
                f"{resultado.get('tipo_animal', '')} "
                f"{client_data}"
            ),
            mapa=mapa,
            nome_mapa="racas64017",
            fallback=fallback
        )

        if not codigo:
            raise Exception(
                "Não foi possível resolver a raça para produto 64017 e não existe "
                "fallbackCodigo configurado em swissre_rules.racas64017."
            )

        return str(codigo)

    def aplicar_limite_valor_por_utilizacao(codigo_utilizacao: str, valor_animal: float, rules: dict) -> dict:
        """
        Mantida apenas por compatibilidade. A montagem final dos valores segurados
        deve ser feita por montar_coverages_por_regras(), usando 100% das regras
        do banco.
        """
        codigo_utilizacao = str(codigo_utilizacao)
        regra = rules.get("limitesPorUtilizacao", {}).get(codigo_utilizacao)

        if regra:
            limite = SwissReAutomation.to_float(
                regra.get("valorMaximoBasica"),
                f"limitesPorUtilizacao.{codigo_utilizacao}.valorMaximoBasica"
            )
            return {
                "valor_basica": min(valor_animal, limite),
                "limite_aplicado": limite,
                "descricao_regra": regra.get("descricao")
            }

        return {
            "valor_basica": valor_animal,
            "limite_aplicado": None,
            "descricao_regra": None
        }

    def calcular_idade_meses(data_nascimento: str) -> int:
        formatos_aceitos = [
            "%d/%m/%Y",
            "%Y-%m-%d",
            "%d-%m-%Y",
            "%Y-%m-%dT%H:%M:%S"
        ]

        data_convertida = None

        for formato in formatos_aceitos:
            try:
                data_convertida = datetime.strptime(str(data_nascimento).strip(), formato).date()
                break
            except ValueError:
                pass

        if data_convertida is None:
            raise Exception(f"Data de nascimento inválida para cálculo de idade: {data_nascimento}")

        hoje = datetime.now().date()

        idade_meses = (hoje.year - data_convertida.year) * 12 + (hoje.month - data_convertida.month)

        if hoje.day < data_convertida.day:
            idade_meses -= 1

        return max(idade_meses, 0)

    def validar_idade_por_utilizacao(codigo_utilizacao: str, data_nascimento: str, rules: dict):
        """
        Valida idade mínima e máxima conforme utilização usando exclusivamente
        swissre_rules.idadePorUtilizacao.
        """
        codigo_utilizacao = str(codigo_utilizacao)
        regras = rules.get("idadePorUtilizacao", {})

        if not codigo_utilizacao or codigo_utilizacao not in regras:
            return {
                "valido": False,
                "mensagem": (
                    "Não foi possível enquadrar automaticamente a utilização do animal "
                    "conforme as regras da seguradora."
                ),
                "idade_meses": None,
                "limite_meses": None,
                "utilizacao": None
            }

        idade_meses = SwissReAutomation.calcular_idade_meses(data_nascimento)
        regra = regras[codigo_utilizacao]

        descricao = regra.get("descricao", codigo_utilizacao)
        min_meses = SwissReAutomation.to_int(regra.get("minMeses", 4), f"idadePorUtilizacao.{codigo_utilizacao}.minMeses")
        max_meses = SwissReAutomation.to_int(regra.get("maxMeses"), f"idadePorUtilizacao.{codigo_utilizacao}.maxMeses")

        if idade_meses < min_meses:
            return {
                "valido": False,
                "mensagem": (
                    f"O animal possui {idade_meses} meses. "
                    f"Para a utilização {descricao}, a idade mínima aceita é de "
                    f"{min_meses} meses."
                ),
                "idade_meses": idade_meses,
                "limite_meses": min_meses,
                "utilizacao": descricao
            }

        if idade_meses > max_meses:
            return {
                "valido": False,
                "mensagem": (
                    f"O animal possui {idade_meses} meses. "
                    f"Para a utilização {descricao}, a idade máxima aceita é de "
                    f"{max_meses} meses."
                ),
                "idade_meses": idade_meses,
                "limite_meses": max_meses,
                "utilizacao": descricao
            }

        return {
            "valido": True,
            "mensagem": "Idade válida para a utilização informada.",
            "idade_meses": idade_meses,
            "limite_meses": max_meses,
            "utilizacao": descricao
        }

    def normalizar_texto_busca(texto):
        import unicodedata

        texto = str(texto or "").lower().strip()
        texto = unicodedata.normalize("NFD", texto)
        texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")

        caracteres = ["-", "_", "(", ")", ".", ",", "/", "\\"]
        for c in caracteres:
            texto = texto.replace(c, " ")

        texto = " ".join(texto.split())
        return texto

    def resolver_sexo_animal(valor_sexo: str, texto_original: str, rules: dict) -> str:
        """
        Resolve o código do sexo usando swissre_rules.sexoAnimal.

        Exemplo esperado:
        "sexoAnimal": {
        "descricoes": {"1": "Macho", "2": "Fêmea", "3": "Castrado"},
        "fallbackCodigo": "2",
        "termos": {"macho": "1", "femea": "2", "castrado": "3"}
        }
        """

        mapa = SwissReAutomation.obter_secao_mapeamento(rules, "sexoAnimal")
        fallback = SwissReAutomation.obter_fallback_codigo(rules, "sexoAnimal")

        codigo = SwissReAutomation.buscar_codigo_por_texto(
            texto_busca=f"{valor_sexo} {texto_original}",
            mapa=mapa,
            nome_mapa="sexoAnimal",
            fallback=fallback
        )

        if not codigo:
            raise Exception(
                "Não foi possível resolver sexo_animal e não existe fallbackCodigo "
                "configurado em swissre_rules.sexoAnimal."
            )

        return str(codigo)

    def resolver_utilizacao_animal(valor_utilizacao: str, texto_original: str, rules: dict) -> str:
        """
        Resolve o código end_tpenq usando swissre_rules.utilizacoesEquinos.
        O banco deve conter o mapa termo -> código, mesmo quando os códigos se repetem.
        """

        mapa = SwissReAutomation.obter_secao_mapeamento(rules, "utilizacoesEquinos")

        return SwissReAutomation.buscar_codigo_por_texto(
            texto_busca=f"{valor_utilizacao} {texto_original}",
            mapa=mapa,
            nome_mapa="utilizacoesEquinos"
        )

    def resolver_raca_animal(valor_raca: str, texto_original: str, rules: dict) -> str:
        """
        Resolve o código end_classenq usando swissre_rules.racasEquinos.
        """

        mapa = SwissReAutomation.obter_secao_mapeamento(rules, "racasEquinos")
        fallback = SwissReAutomation.obter_fallback_codigo(rules, "racasEquinos")

        codigo = SwissReAutomation.buscar_codigo_por_texto(
            texto_busca=f"{valor_raca} {texto_original}",
            mapa=mapa,
            nome_mapa="racasEquinos",
            fallback=fallback
        )

        if not codigo:
            raise Exception(
                "Não foi possível resolver raca_animal e não existe fallbackCodigo "
                "configurado em swissre_rules.racasEquinos."
            )

        return str(codigo)

    def subtrair_meses(data_base: date, meses: int) -> date:
        mes = data_base.month - meses
        ano = data_base.year + (mes - 1) // 12
        mes = (mes - 1) % 12 + 1

        ultimo_dia_mes = calendar.monthrange(ano, mes)[1]
        dia = min(data_base.day, ultimo_dia_mes)

        return date(ano, mes, dia)

    def ajustar_data_nascimento_min_4_meses(data_nascimento) -> str:
        """
        Aceita:
        - Data: 17/10/2023, 2023-10-17
        - Idade: 2 anos, 9 anos, 6 meses, 1 ano e 3 meses

        Retorna sempre no formato DD/MM/YYYY.
        Se a idade/data indicar menos de 4 meses, ajusta para 4 meses atrás.
        """

        hoje = datetime.now().date()

        if not data_nascimento:
            data_ajustada = SwissReAutomation.subtrair_meses(hoje, 4)
            return data_ajustada.strftime("%d/%m/%Y")

        texto = str(data_nascimento).lower().strip()

        # Normalizações básicas
        texto = texto.replace("mês", "mes")
        texto = texto.replace("meses", "mes")
        texto = texto.replace("ano(s)", "anos")
        texto = texto.replace("mes(es)", "mes")

        # Caso venha como idade textual: "2 anos", "6 meses", "1 ano e 3 meses"
        match_anos = re.search(r"(\d+)\s*anos?", texto)
        match_meses = re.search(r"(\d+)\s*mes", texto)

        if match_anos or match_meses:
            anos = int(match_anos.group(1)) if match_anos else 0
            meses = int(match_meses.group(1)) if match_meses else 0

            total_meses = (anos * 12) + meses

            # Regra SwissRe: mínimo 4 meses
            if total_meses < 4:
                total_meses = 4

            data_convertida = SwissReAutomation.subtrair_meses(hoje, total_meses)
            return data_convertida.strftime("%d/%m/%Y")

        # Caso venha como data
        formatos_aceitos = [
            "%d/%m/%Y",
            "%Y-%m-%d",
            "%d-%m-%Y",
            "%Y-%m-%dT%H:%M:%S"
        ]

        data_convertida = None

        for formato in formatos_aceitos:
            try:
                data_convertida = datetime.strptime(texto, formato).date()
                break
            except ValueError:
                pass

        if data_convertida is None:
            raise Exception(f"Data de nascimento inválida: {data_nascimento}")

        data_limite_4_meses = SwissReAutomation.subtrair_meses(hoje, 4)

        if data_convertida > data_limite_4_meses:
            data_convertida = data_limite_4_meses

        return data_convertida.strftime("%d/%m/%Y")

    def definir_product_id(resultado: dict, texto_original, rules: dict) -> str:
        """
        Define o productId conforme o tipo do animal.
        Os productIds são lidos de swissre_rules.general.
        """

        import unicodedata
        import json
        import re

        def normalizar_texto(texto):
            if isinstance(texto, dict):
                texto = json.dumps(texto, ensure_ascii=False)

            texto = str(texto or "").lower().strip()
            texto = unicodedata.normalize("NFD", texto)
            texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
            return texto

        tipo_animal = normalizar_texto(resultado.get("tipo_animal", ""))
        raca_animal = normalizar_texto(resultado.get("raca_animal", ""))
        texto = normalizar_texto(texto_original)

        texto_completo = f"{tipo_animal} {raca_animal} {texto}"

        termos_produto_mula = rules.get("termosProdutoMula")
        if not isinstance(termos_produto_mula, list) or not termos_produto_mula:
            raise Exception(
                "Seção obrigatória ausente ou inválida no banco: "
                "swissre_rules.termosProdutoMula"
            )

        product_id_mula = str(SwissReAutomation.obter_parametro_geral(rules, "productIdMula"))
        product_id_cavalo = str(SwissReAutomation.obter_parametro_geral(rules, "productIdCavalo"))

        for termo in termos_produto_mula:
            termo_norm = SwissReAutomation.normalizar_texto_busca(termo)
            if termo_norm and (
                re.search(rf"\b{re.escape(termo_norm)}\b", texto_completo) is not None
                or termo_norm in texto_completo
            ):
                return product_id_mula

        return product_id_cavalo

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
            "uf",
            "valor",
            "nome",
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
                dados = SwissReAutomation.normalizar_retorno_json(json_dados)

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
        from app.bot.swissre_rules_repository import get_active_rules

        logger.info(f"Inicio Fluxo de Cotação SwissRe: {client_data}")

        prompt = f"""
        Nome:
        Conversão de dados de texto em dados categorizados em formato de json.

        Descrição:
        De acordo com os dados enviados, extraia as seguintes informações do texto e retorne apenas JSON puro, sem texto adicional.

        Retorne as chaves:
        'uf', 'valor', 'nome', 'email', 'tipo_animal', 'data_nascimento', 'utilizacao', 'sexo_animal', 'raca_animal'.

        Instruções:
        valor = Valor do animal a ser cotado o seguro.
        nome = Nome do solicitante.
        uf = unidade de federação do estado.
        tipo_animal = Tipo do animal informado.
        data_nascimento = Data de nascimento do animal, se informada.
        utilizacao = Finalidade/uso do animal. Exemplos: Exposição, Lazer, Reprodução, Corrida, Salto, Trabalho, Vaquejada.
        sexo_animal = Sexo do animal. Retornar Macho, Fêmea ou Castrado.
        raca_animal = Raça do animal. Exemplo: Appaloosa, Mangalarga, Quarto de Milha, Crioulo, SRD.

        Regras:
        - Se algum campo não for encontrado e não puder ser deduzido, deixe vazio.
        - Para raca_animal, se o texto informar SRD, sem raça ou mestiço, retornar "Sem Raça Definida".
        - Os dados como 'cep','rua','numero','bairro','cidade' deverão ser considerados da prefeitura da capital do estado da UF.
        - data_nascimento: Se o cliente informar uma data, retornar no formato DD/MM/AAAA.
        - Se o cliente informar idade, como "9 anos", "6 meses" ou "1 ano e 3 meses", retornar exatamente a idade informada no campo data_nascimento.

        Texto: {client_data}
        """

        try:
            logger.info(f"Nome do Animal: {client_data.get('nome_animal')}")

            rules = get_active_rules()
            general_rules = rules.get("general", {})

            resultado = SwissReAutomation.extrair_dados_chatgpt(prompt)
            if not resultado:
                return {
                    "success": False,
                    "requires_agent": True,
                    "message": "Não foi possível extrair os dados obrigatórios para cotação.",
                    "business_rule": "extracao_dados_chatgpt"
                }

            cpf = str(SwissReAutomation.obter_parametro_geral(rules, "cpf"))
            product_version_id = str(SwissReAutomation.obter_parametro_geral(rules, "productVersionId"))
            cod_plano_padrao = str(SwissReAutomation.obter_parametro_geral(rules, "codPlanoPadrao"))
            cod_afinidade = str(SwissReAutomation.obter_parametro_geral(rules, "codAfinidade"))

            vigencia_dias = SwissReAutomation.to_int(
                SwissReAutomation.obter_parametro_geral(rules, "vigenciaDias"),
                "general.vigenciaDias"
            )
            installment_number = SwissReAutomation.to_int(
                SwissReAutomation.obter_parametro_geral(rules, "installmentNumber"),
                "general.installmentNumber"
            )
            number_of_installments = SwissReAutomation.to_int(
                SwissReAutomation.obter_parametro_geral(rules, "numberOfInstallments"),
                "general.numberOfInstallments"
            )

            product_id = SwissReAutomation.definir_product_id(resultado, client_data, rules)

            logger.info(f"Tipo animal identificado: {resultado.get('tipo_animal')}")
            logger.info(f"ProductId definido: {product_id}")

            codigo_sexo = SwissReAutomation.resolver_sexo_animal(
                resultado.get("sexo_animal"),
                client_data,
                rules
            )

            if str(product_id) == str(SwissReAutomation.obter_parametro_geral(rules, "productIdMula")):
                regra_utilizacao_64017 = SwissReAutomation.resolver_utilizacao_64017(resultado, client_data, rules)

                if not regra_utilizacao_64017["valido"]:
                    logger.warning(regra_utilizacao_64017["mensagem"])

                    return {
                        "success": False,
                        "requires_agent": True,
                        "message": regra_utilizacao_64017["mensagem"],
                        "business_rule": "utilizacao_64017_nao_mapeada"
                    }

                codigo_utilizacao = regra_utilizacao_64017["codigo"]
                codigo_raca = SwissReAutomation.resolver_raca_64017(resultado, client_data, rules)

                logger.info(
                    f"Utilização 64017 identificada: "
                    f"{regra_utilizacao_64017['descricao']} -> {codigo_utilizacao}"
                )
                logger.info(f"Raça 64017 identificada -> {codigo_raca}")

            else:
                codigo_utilizacao = SwissReAutomation.resolver_utilizacao_animal(
                    resultado.get("utilizacao"),
                    client_data,
                    rules
                )
                codigo_raca = SwissReAutomation.resolver_raca_animal(
                    resultado.get("raca_animal"),
                    client_data,
                    rules
                )

                logger.info(f"Utilização identificada: {resultado.get('utilizacao')} -> {codigo_utilizacao}")
                logger.info(f"Raça identificada: {resultado.get('raca_animal')} -> {codigo_raca}")

            logger.info(f"Sexo identificado: {resultado.get('sexo_animal')} -> {codigo_sexo}")

            data_nascimento_animal = SwissReAutomation.ajustar_data_nascimento_min_4_meses(
                resultado.get("data_nascimento") or client_data.get("data_nascimento")
            )

            logger.info(
                f"Data nascimento original: "
                f"{resultado.get('data_nascimento') or client_data.get('data_nascimento')}"
            )
            logger.info(f"Data nascimento convertida para SwissRe: {data_nascimento_animal}")

            if not codigo_utilizacao:
                mensagem_regra = (
                    "Não foi possível identificar automaticamente a utilização principal do animal "
                    "conforme as regras de aceitação da seguradora."
                )

                logger.warning(mensagem_regra)

                return {
                    "success": False,
                    "requires_agent": True,
                    "message": mensagem_regra,
                    "business_rule": "utilizacao_nao_identificada"
                }

            validacao_idade = SwissReAutomation.validar_idade_por_utilizacao(
                codigo_utilizacao,
                data_nascimento_animal,
                rules
            )

            if not validacao_idade["valido"]:
                logger.warning(f"Regra de aceitação recusada: {validacao_idade}")

                return {
                    "success": False,
                    "requires_agent": True,
                    "message": validacao_idade["mensagem"],
                    "business_rule": "idade_por_utilizacao",
                    "validacao": validacao_idade
                }

            uf = str(resultado["uf"]).upper().strip()
            endereco = DADOS_ESTADOS.get(uf)
            if not endereco:
                return {
                    "success": False,
                    "requires_agent": True,
                    "message": f"UF não encontrada na base de endereços: {uf}",
                    "business_rule": "uf_nao_mapeada"
                }

            logger.info(f"Resultado dados categorizados: {resultado}")

            valor_animal = SwissReAutomation.normalizar_valor_monetario(resultado["valor"])

            coverages = SwissReAutomation.montar_coverages_por_regras(
                rules=rules,
                product_id=product_id,
                cod_plano=cod_plano_padrao,
                codigo_utilizacao=codigo_utilizacao,
                valor_animal=valor_animal
            )

            logger.info(f"Valor informado pelo usuário: {valor_animal}")
            logger.info(f"Utilização código: {codigo_utilizacao}")
            logger.info(f"Coverages montadas pelo banco para productId {product_id}: {coverages}")

            now = datetime.now()
            start_date = now.strftime("%Y-%m-%d")
            expire_date = (now + timedelta(days=vigencia_dias)).strftime("%Y-%m-%d")
            first_maturity = now.strftime("%Y-%m-%dT00:00:00")

            payload = {
                "productId": product_id,
                "productVersionId": product_version_id,
                "entityTypeId": str(SwissReAutomation.obter_parametro_geral(rules, "entityTypeId")),
                "endorsementTypeId": str(SwissReAutomation.obter_parametro_geral(rules, "endorsementTypeId")),
                "calculationTypeId": str(SwissReAutomation.obter_parametro_geral(rules, "calculationTypeId")),
                "installmentNumber": installment_number,
                "chargeTypeId": str(SwissReAutomation.obter_parametro_geral(rules, "chargeTypeId")),
                "installmentDetails": {
                    "interest": SwissReAutomation.to_float(
                        SwissReAutomation.obter_parametro_geral(rules, "interest"),
                        "general.interest"
                    ),
                    "netPremium": SwissReAutomation.to_float(
                        SwissReAutomation.obter_parametro_geral(rules, "netPremium"),
                        "general.netPremium"
                    ),
                    "dateFirstMaturity": first_maturity,
                    "numberOfInstallments": number_of_installments,
                    "firstInstallmentValue": SwissReAutomation.to_float(
                        SwissReAutomation.obter_parametro_geral(rules, "firstInstallmentValue"),
                        "general.firstInstallmentValue"
                    )
                },
                "startDate": start_date,
                "expireDate": expire_date,
                "exemptionTypeId": str(SwissReAutomation.obter_parametro_geral(rules, "exemptionTypeId")),
                "hasFederalSubsidy": SwissReAutomation.to_bool(
                    SwissReAutomation.obter_parametro_geral(rules, "hasFederalSubsidy")
                ),
                "hasStateSubsidy": SwissReAutomation.to_bool(
                    SwissReAutomation.obter_parametro_geral(rules, "hasStateSubsidy")
                ),
                "hasMunicipalSubsidy": SwissReAutomation.to_bool(
                    SwissReAutomation.obter_parametro_geral(rules, "hasMunicipalSubsidy")
                ),
                "currencyId": str(SwissReAutomation.obter_parametro_geral(rules, "currencyId")),
                "surveyor": None,
                "policyholder": None,
                "insured": {
                    "name": resultado["nome"],
                    "documentId": cpf
                },
                "beneficiary": {
                    "beneficiaryName": resultado["nome"],
                    "cpfNumber": cpf
                },
                "brokers": [
                    {
                        "id": str(SwissReAutomation.obter_parametro_geral(rules, "brokerCode")),
                        "comission": SwissReAutomation.to_float(
                            SwissReAutomation.obter_parametro_geral(rules, "brokerComission"),
                            "general.brokerComission"
                        )
                    }
                ],
                "salesOrganization": {
                    "brokerId": str(SwissReAutomation.obter_parametro_geral(rules, "brokerId")),
                    "agencyId": str(SwissReAutomation.obter_parametro_geral(rules, "agencyId")),
                    "accountNumber": str(SwissReAutomation.obter_parametro_geral(rules, "accountNumber")),
                    "postServiceId": str(SwissReAutomation.obter_parametro_geral(rules, "postServiceId"))
                },
                "items": [
                    {
                        "ItemActionType": "New",
                        "DiscountAndAggrave": 0,
                        "dynamicFields": [
                            {
                                "id": "end_nomris",
                                "value": client_data.get("nome_animal")
                            },
                            {
                                "id": "end_identris",
                                "value": "-"
                            },
                            {
                                "id": "end_dataris",
                                "value": data_nascimento_animal
                            },
                            {
                                "id": "end_tpenq",
                                "value": codigo_utilizacao
                            },
                            {
                                "id": "end_classenq",
                                "value": codigo_raca
                            },
                            {
                                "id": "end_tplocal",
                                "value": codigo_sexo
                            },
                            {
                                "id": "cod_plano",
                                "value": cod_plano_padrao
                            },
                            {
                                "id": "cod_afinidade",
                                "value": cod_afinidade
                            }
                        ],
                        "coverages": coverages,
                        "riskArea": {
                            "cep": endereco["cep"],
                            "address": endereco["rua"],
                            "numberOfAddress": endereco["numero"],
                            "complement": None,
                            "district": endereco["bairro"],
                            "unitFederated": uf,
                            "city": endereco["cidade"]
                        }
                    }
                ]
            }

            logger.info("Capturar Token")
            data = {
                "grant_type": "client_credentials",
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET
            }
            response = requests.post(TOKEN_URL, data=data, timeout=60)
            response.raise_for_status()
            token = response.json()["access_token"]

            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }

            logger.info("Envio requisição para formalizar cotacao")
            logger.info("PAYLOAD ENVIADO:")
            logger.info(json.dumps(payload, ensure_ascii=False, indent=2))

            quotation_response = requests.post(API_URL, headers=headers, json=payload, timeout=300)

            if not quotation_response.ok:
                try:
                    erro_api = quotation_response.json()
                except ValueError:
                    erro_api = {"raw_text": quotation_response.text}

                if isinstance(erro_api, dict):
                    mensagem_erro = (
                        erro_api.get("CombinedMessages")
                        or erro_api.get("message")
                        or erro_api.get("error")
                        or erro_api.get("error_description")
                        or erro_api.get("raw_text")
                        or "Erro não detalhado pela API."
                    )
                else:
                    mensagem_erro = str(erro_api)

                logger.error(
                    f"SwissRe retornou erro HTTP {quotation_response.status_code}: "
                    f"{mensagem_erro}"
                )

                return {
                    "success": False,
                    "message": (
                        f"SwissRe retornou erro HTTP {quotation_response.status_code}: "
                        f"{mensagem_erro}"
                    ),
                    "status_code": quotation_response.status_code,
                    "api_response": erro_api,
                    "api_text": quotation_response.text
                }

            try:
                dados = quotation_response.json()
            except ValueError:
                logger.error(f"SwissRe retornou resposta não JSON: {quotation_response.text}")
                return {
                    "success": False,
                    "message": "SwissRe retornou resposta inválida: corpo não é JSON.",
                    "status_code": quotation_response.status_code,
                    "api_response": None,
                    "api_text": quotation_response.text
                }

            if not dados.get("IsValid", False):
                erro_api = (dados.get("CombinedMessages") or "Cotação recusada pela SwissRe.").strip()
                logger.info(erro_api)
                return {
                    "success": False,
                    "message": f"SwissRe recusou a cotação: {erro_api}",
                    "api_response": dados
                }

            contractNumber = dados["Response"]["contractNumber"]
            issuanceId = dados["Response"]["issuanceId"]
            logger.info(f"Status Code: {quotation_response.status_code}")
            logger.info(f"Response: {dados}")

            payload_doc = {
                "typeId": str(SwissReAutomation.obter_parametro_geral(rules, "documentTypeId")),
                "issuanceId": issuanceId,
                "contractNumber": contractNumber,
                "proposalNumber": ""
            }

            logger.info(f"Cotacao gerada {contractNumber}")
            resultado_documento = SwissReAutomation.gerar_documento_com_retry(
                url=API_URL_DOCUMENT,
                headers=headers,
                payload=payload_doc,
                tentativas=4
            )

            if not resultado_documento.get("success"):
                logger.warning(
                    "Cotação criada, mas PDF ficou pendente. Cotação: %s. Erro: %s",
                    contractNumber,
                    resultado_documento.get("error")
                )

                return {
                    "success": True,
                    "pdf_pending": True,
                    "requires_agent": True,
                    "message": (
                        "Cotação criada com sucesso, mas o PDF ainda não ficou disponível. "
                        "Um atendente irá acompanhar e enviar a proposta."
                    ),
                    "quotation_number": contractNumber,
                    "issuance_id": issuanceId,
                    "document_error": resultado_documento.get("error"),
                    "document_status_code": resultado_documento.get("status_code"),
                    "document_response": resultado_documento.get("body")
                }

            response_doc = resultado_documento["response"]

            logger.info(f"Status Code documento: {response_doc.status_code}")

            path_file = os.path.join(path_bot_download, f"Cotacao_{contractNumber}.pdf")
            if response_doc.status_code == 200:
                with open(path_file, "wb") as f:
                    f.write(response_doc.content)

                logger.info(f"Documento salvo em: {path_file}")

                pdf_id = salvar_pdf_mongo(path_file, contractNumber)
                logger.info(f"PDF salvo no MongoDB com ID: {pdf_id}")

                return {
                    "success": True,
                    "pdf_path": path_file,
                    "pdf_id": pdf_id,
                    "message": "Cotação gerada com sucesso",
                    "quotation_number": contractNumber,
                }

        except Exception as e:
            logger.error(f"❌ Erro na automação SwissRe: {str(e)}")
            return {
                "success": False,
                "message": f"Erro na automação: {str(e)}"
            }
