# -*- coding: utf-8 -*-
"""
Extrator de Dados Inteligente - NOVA VERSÃO
Usa IA para extrair informações das mensagens do usuário
Campos atualizados conforme novo roteiro (sem e-mail)
"""

import os
import re
import json
import logging
from typing import Dict, Optional
from openai import OpenAI

logger = logging.getLogger(__name__)


class DataExtractor:
    """
    Extrai dados estruturados de mensagens de texto usando IA
    """

    def __init__(self):
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.client = None

        if self.openai_api_key:
            self.client = OpenAI(api_key=self.openai_api_key)
            logger.info("DataExtractor inicializado com OpenAI")
        else:
            logger.warning("OpenAI API key não encontrada, usando extração simples")

    def extract_data(self, message: str, existing_data: Optional[Dict] = None) -> Dict:
        """
        Extrai dados da mensagem e mescla com dados existentes
        """
        if self.client:
            return self._extract_with_ai(message, existing_data)
        else:
            return self._extract_simple(message, existing_data)

    def _extract_with_ai(self, message: str, existing_data: Optional[Dict]) -> Dict:
        """Extrai dados usando OpenAI"""
        try:
            logger.info("Extraindo dados usando OpenAI")

            existing_context = ""
            if existing_data:
                existing_context = "\n\nDados já coletados anteriormente:\n" + json.dumps(
                    existing_data, ensure_ascii=False, indent=2
                )

            system_prompt = f"""Você é um assistente especializado em extrair dados estruturados de mensagens de texto.

Sua tarefa é extrair informações para cotação de seguros de equinos (cavalos).

CAMPOS OBRIGATÓRIOS:
- nome_solicitante: Nome completo do solicitante (pessoa que está pedindo a cotação)
- nome_animal: Nome do animal (cavalo/égua)
- valor_animal: Valor do animal em reais (apenas números, sem R$ ou pontos)
- raca: Raça do animal (ex: Quarto de Milha, Mangalarga, Crioulo, etc.)
- data_nascimento: Data de nascimento no formato DD/MM/AAAA
- sexo: Sexo do animal (inteiro, castrado ou fêmea)
- utilizacao: Utilização do animal (lazer, salto, laço, corrida, vaquejada, tambor, adestramento, hipismo, reprodução, etc.)
- uf: Estado onde o cavalo fica alojado (sigla com 2 letras, ex: SP, MG, RJ)

REGRAS IMPORTANTES:
1. Extraia APENAS informações que estão EXPLICITAMENTE na mensagem
2. NUNCA invente ou assuma dados que não foram fornecidos
3. Se um campo não foi mencionado, NÃO inclua no JSON
4. Se houver dados anteriores, preserve-os e atualize apenas os novos
5. Para valor_animal, extraia apenas números (sem R$, pontos ou vírgulas de milhar)
6. Para sexo, normalize para: "inteiro", "castrado" ou "fêmea"
7. Para uf, normalize para sigla de 2 letras maiúsculas

{existing_context}

Responda APENAS com um JSON válido contendo os campos extraídos.
Exemplo:
{{
  "nome_solicitante": "João Silva",
  "nome_animal": "Relâmpago",
  "valor_animal": "50000",
  "raca": "Quarto de Milha",
  "sexo": "inteiro",
  "uf": "SP"
}}"""

            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": message}
                ],
                max_tokens=400,
                temperature=0.1
            )

            response_text = response.choices[0].message.content.strip()

            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                extracted_data = json.loads(json_str)

                # Mesclar com dados existentes
                if existing_data:
                    merged_data = existing_data.copy()
                    for key, value in extracted_data.items():
                        if value and str(value).strip():
                            merged_data[key] = value
                    return merged_data
                else:
                    return extracted_data
            else:
                logger.warning("Não foi possível extrair JSON da resposta da IA")
                return existing_data or {}

        except Exception as e:
            logger.error(f"Erro na extração com IA: {str(e)}")
            return self._extract_simple(message, existing_data)

    def _extract_simple(self, message: str, existing_data: Optional[Dict]) -> Dict:
        """
        Extração simples usando regex (fallback quando IA não está disponível)
        """
        data = existing_data.copy() if existing_data else {}
        message_lower = message.lower()

        patterns = {
            'nome_solicitante': [
                r'(?:nome solicitante|meu nome|me chamo|sou)[:\s]+([a-záàâãéêíóôõúç\s]+?)(?:\n|$|,|\.|cpf)',
                r'solicitante[:\s]+([a-záàâãéêíóôõúç\s]+?)(?:\n|$|,|\.|cpf)'
            ],
            'nome_animal': [
                r'(?:nome do animal|nome do cavalo|nome da égua|animal)[:\s]+([a-záàâãéêíóôõúç\s]+?)(?:\n|$|,|\.)',
                r'(?:chama|chamado)[:\s]+([a-záàâãéêíóôõúç\s]+?)(?:\n|$|,|\.)'
            ],
            'valor_animal': [
                r'valor[:\s]*r?\$?\s*([0-9.,]+)',
                r'vale[:\s]*r?\$?\s*([0-9.,]+)',
                r'r\$\s*([0-9.,]+)'
            ],
            'raca': [
                r'raça[:\s]+([a-záàâãéêíóôõúç\s]+?)(?:\n|$|,|\.)',
                r'\b(quarto de milha|mangalarga|puro sangue|crioulo|campolina|brasileiro de hipismo|lusitano|paint horse|appaloosa|árabe)\b'
            ],
            'data_nascimento': [
                r'(?:nascimento|nasceu|data)[:\s]*(\d{1,2}/\d{1,2}/\d{4})',
                r'(\d{1,2}/\d{1,2}/\d{4})'
            ],
            'sexo': [
                r'\b(inteiro|castrado|fêmea|femea|macho|égua|egua)\b'
            ],
            'utilizacao': [
                r'(?:utilização|utilizacao|uso|utiliza)[:\s]+([a-záàâãéêíóôõúç\s]+?)(?:\n|$|,|\.)',
                r'\b(lazer|salto|laço|laco|corrida|trabalho|esporte|competição|exposição|vaquejada|tambor|baliza|adestramento|hipismo|reprodução|reproduçao)\b'
            ],
            'uf': [
                r'(?:uf|estado)[:\s]*([a-z]{2})\b',
            ]
        }

        for field, pattern_list in patterns.items():
            if field not in data or not data[field]:
                for pattern in pattern_list:
                    match = re.search(pattern, message_lower, re.IGNORECASE)
                    if match:
                        value = match.group(1).strip()

                        if field == 'valor_animal':
                            value = re.sub(r'[^\d]', '', value)
                        elif field == 'uf':
                            value = value.upper()
                        elif field == 'sexo':
                            # Normalizar sexo
                            sexo_map = {
                                'macho': 'inteiro',
                                'égua': 'fêmea',
                                'egua': 'fêmea',
                                'femea': 'fêmea'
                            }
                            value = sexo_map.get(value.lower(), value.lower())

                        data[field] = value
                        logger.info(f"Extraído {field}: {value}")
                        break

        return data

    def validate_data(self, data: Dict) -> tuple:
        """
        Valida os dados extraídos
        """
        errors = []

        # Validar data de nascimento
        if 'data_nascimento' in data and data['data_nascimento']:
            data_nasc = data['data_nascimento']
            if not re.match(r'^\d{2}/\d{2}/\d{4}$', data_nasc):
                errors.append("Data de nascimento deve estar no formato DD/MM/AAAA")

        # Validar UF
        if 'uf' in data and data['uf']:
            uf = data['uf'].upper()
            ufs_validas = [
                'AC', 'AL', 'AP', 'AM', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA',
                'MT', 'MS', 'MG', 'PA', 'PB', 'PR', 'PE', 'PI', 'RJ', 'RN',
                'RS', 'RO', 'RR', 'SC', 'SP', 'SE', 'TO'
            ]
            if uf not in ufs_validas:
                errors.append(f"UF inválida: {uf}")

        # Validar valor do animal
        if 'valor_animal' in data and data['valor_animal']:
            try:
                valor = int(re.sub(r'[^\d]', '', str(data['valor_animal'])))
                if valor <= 0:
                    errors.append("Valor do animal deve ser maior que zero")
            except ValueError:
                errors.append("Valor do animal deve ser um número válido")

        # Validar sexo
        if 'sexo' in data and data['sexo']:
            sexo = data['sexo'].lower()
            if sexo not in ['inteiro', 'castrado', 'fêmea', 'femea']:
                errors.append("Sexo deve ser: inteiro, castrado ou fêmea")

        return len(errors) == 0, errors


# Instância global do extrator
data_extractor = DataExtractor()
