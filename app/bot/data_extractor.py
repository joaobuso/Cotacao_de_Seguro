# -*- coding: utf-8 -*-
"""
Extrator de Dados Inteligente
Usa IA para extrair informações das mensagens do usuário
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
        """Inicializa o extrator com OpenAI"""
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
        
        Args:
            message: Mensagem do usuário
            existing_data: Dados já coletados anteriormente
            
        Returns:
            Dict com dados extraídos e mesclados
        """
        if self.client:
            return self._extract_with_ai(message, existing_data)
        else:
            return self._extract_simple(message, existing_data)
    
    def _extract_with_ai(self, message: str, existing_data: Optional[Dict]) -> Dict:
        """Extrai dados usando OpenAI"""
        try:
            # Preparar contexto com dados existentes
            existing_context = ""
            if existing_data:
                existing_context = "\n\nDados já coletados anteriormente:\n" + json.dumps(
                    existing_data, ensure_ascii=False, indent=2
                )
            
            system_prompt = f"""Você é um assistente especializado em extrair dados estruturados de mensagens de texto.

Sua tarefa é extrair informações para cotação de seguros de equinos.

CAMPOS OBRIGATÓRIOS:
- nome_solicitante: Nome completo do solicitante
- cpf_solicitante: CPF do solicitante (apenas números)
- nome_animal: Nome do animal
- valor_animal: Valor do animal em reais (apenas números, sem R$ ou pontos)
- raca: Raça do animal
- data_nascimento: Data de nascimento no formato DD/MM/AAAA
- sexo: Sexo do animal (inteiro, castrado ou fêmea)
- utilizacao: Utilização do animal (lazer, salto, laço, corrida, etc)
- rua: Nome da rua
- numero: Número do endereço
- bairro: Bairro
- cidade: Cidade
- uf: Estado (sigla com 2 letras)
- cep: CEP (apenas números)

REGRAS IMPORTANTES:
1. Extraia APENAS informações que estão EXPLICITAMENTE na mensagem
2. NUNCA invente ou assuma dados que não foram fornecidos
3. Se um campo não foi mencionado, deixe-o vazio ou não inclua no JSON
4. Se houver dados anteriores, preserve-os e atualize apenas os novos
5. Normalize os dados (remova caracteres especiais de CPF e CEP, padronize datas)

{existing_context}

Responda APENAS com um JSON válido contendo os campos extraídos.
Exemplo:
{{
  "nome_solicitante": "João Silva",
  "cpf_solicitante": "12345678900",
  "nome_animal": "Relâmpago",
  "valor_animal": "50000",
  "raca": "Quarto de Milha"
}}"""
            
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": message}
                ],
                max_tokens=300,
                temperature=0.1
            )
            
            # Extrair JSON da resposta
            response_text = response.choices[0].message.content.strip()
            
            # Tentar encontrar JSON na resposta
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                extracted_data = json.loads(json_str)
                
                # Mesclar com dados existentes
                if existing_data:
                    merged_data = existing_data.copy()
                    # Atualizar apenas campos não vazios
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
        
        # Padrões de extração por regex
        patterns = {
            'nome_solicitante': [
                r'(?:nome solicitante|meu nome|me chamo|sou)[:\s]+([a-záàâãéêíóôõúç\s]+?)(?:\n|$|,|\.|cpf)',
                r'solicitante[:\s]+([a-záàâãéêíóôõúç\s]+?)(?:\n|$|,|\.|cpf)'
            ],
            'cpf_solicitante': [
                r'cpf[:\s]*(\d{3}\.?\d{3}\.?\d{3}-?\d{2})',
                r'(\d{3}\.?\d{3}\.?\d{3}-?\d{2})'
            ],
            'nome_animal': [
                r'(?:nome do animal|nome|cavalo|égua|animal)[:\s]+([a-záàâãéêíóôõúç\s]+?)(?:\n|$|,|\.)',
                r'(?:chama|chamado|nome)[:\s]+([a-záàâãéêíóôõúç\s]+?)(?:\n|$|,|\.)'
            ],
            'valor_animal': [
                r'valor[:\s]*r?\$?\s*([0-9.,]+)',
                r'vale[:\s]*r?\$?\s*([0-9.,]+)',
                r'r\$\s*([0-9.,]+)'
            ],
            'raca': [
                r'raça[:\s]+([a-záàâãéêíóôõúç\s]+?)(?:\n|$|,|\.)',
                r'é\s+um[a]?\s+([a-záàâãéêíóôõúç\s]+?)(?:\n|$|,|\.)'
            ],
            'data_nascimento': [
                r'(?:nascimento|nasceu|data)[:\s]*(\d{1,2}/\d{1,2}/\d{4})',
                r'(\d{1,2}/\d{1,2}/\d{4})'
            ],
            'sexo': [
                r'\b(inteiro|castrado|fêmea|macho|égua)\b'
            ],
            'utilizacao': [
                r'(?:utilização|uso|utiliza)[:\s]+([a-záàâãéêíóôõúç\s]+?)(?:\n|$|,|\.)',
                r'\b(lazer|salto|laço|corrida|trabalho|esporte|competição|exposição)\b'
            ],
            'rua': [
                r'rua[:\s]+([a-záàâãéêíóôõúç\s\d]+?)(?:\n|$|,|número)',
            ],
            'numero': [
                r'(?:número|numero|nº|n)[:\s]*(\d+)',
            ],
            'bairro': [
                r'bairro[:\s]+([a-záàâãéêíóôõúç\s]+?)(?:\n|$|,|cidade)',
            ],
            'cidade': [
                r'cidade[:\s]+([a-záàâãéêíóôõúç\s]+?)(?:\n|$|,|uf|estado)',
            ],
            'uf': [
                r'(?:uf|estado)[:\s]*([a-z]{2})\b',
                r'\b([a-z]{2})\b(?:\s|$)'
            ],
            'cep': [
                r'cep[:\s]*(\d{5}-?\d{3})',
                r'(\d{5}-?\d{3})'
            ]
        }
        
        # Tentar extrair cada campo
        for field, pattern_list in patterns.items():
            # Só tentar extrair se o campo ainda não existe ou está vazio
            if field not in data or not data[field]:
                for pattern in pattern_list:
                    match = re.search(pattern, message_lower, re.IGNORECASE)
                    if match:
                        value = match.group(1).strip()
                        
                        # Normalizar valores específicos
                        if field == 'cpf_solicitante':
                            value = re.sub(r'[^\d]', '', value)
                        elif field == 'valor_animal':
                            value = re.sub(r'[^\d]', '', value)
                        elif field == 'cep':
                            value = re.sub(r'[^\d]', '', value)
                        elif field == 'uf':
                            value = value.upper()
                        
                        data[field] = value
                        logger.info(f"Extraído {field}: {value}")
                        break
        
        return data
    
    def validate_data(self, data: Dict) -> tuple[bool, list]:
        """
        Valida os dados extraídos
        
        Returns:
            tuple: (is_valid, list_of_errors)
        """
        errors = []
        
        # Validar CPF
        if 'cpf_solicitante' in data and data['cpf_solicitante']:
            cpf = data['cpf_solicitante']
            if not re.match(r'^\d{11}$', cpf):
                errors.append("CPF deve conter 11 dígitos")
        
        # Validar CEP
        if 'cep' in data and data['cep']:
            cep = data['cep']
            if not re.match(r'^\d{8}$', cep):
                errors.append("CEP deve conter 8 dígitos")
        
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
                valor = int(data['valor_animal'])
                if valor <= 0:
                    errors.append("Valor do animal deve ser maior que zero")
            except ValueError:
                errors.append("Valor do animal deve ser um número válido")
        
        return len(errors) == 0, errors


# Instância global do extrator
data_extractor = DataExtractor()
