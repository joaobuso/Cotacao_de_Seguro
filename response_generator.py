# -*- coding: utf-8 -*-
"""
Gerador de Respostas Contextuais para Bot de Cotação de Seguros
"""

import os
import json
import re
from openai import OpenAI
import logging
from typing import Dict, List, Tuple
from datetime import datetime
from parser_validacao import normaliza_e_valida

logger = logging.getLogger(__name__)

class ResponseGenerator:
    """Gerador de respostas inteligentes e contextuais"""
    
    def __init__(self):
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.client = OpenAI(api_key=self.openai_api_key)
        
        # Templates de mensagens
        self.templates = {
            'welcome': """🐴 *Olá! Bem-vindo à Equinos Seguros!*

Sou seu assistente virtual e vou te ajudar a fazer a cotação do seguro do seu equino de forma rápida e fácil.

Para gerar sua cotação, preciso de algumas informações sobre seu animal:

📋 *DADOS NECESSÁRIOS:*
• Nome Solicitante
• CPF Solicitante
• Nome do Animal
• Valor do Animal (R$)
• Número de Registro
• Raça
• Data de Nascimento
• Sexo (inteiro, castrado ou fêmea)
• Utilização (lazer, salto, laço, etc.)
• Rua
• Número
• Bairro
• Cidade
• uf
• Cep
                        
Você pode enviar todas as informações de uma vez ou ir enviando aos poucos. Vou te ajudar a organizar tudo! 😊

*Como prefere começar?*""",
            
            'partial_data': """📝 *Obrigado pelas informações!*

*DADOS JÁ COLETADOS:*
{collected_data}

*AINDA PRECISO DE:*
{missing_data}

Pode enviar as informações que faltam. Estou aqui para te ajudar! 😊""",
            
            'complete_data': """✅ *Perfeito! Coletei todas as informações necessárias:*

{complete_data}

🎉 *Sua cotação está sendo processada!*

Em breve você receberá:
• Proposta de seguro personalizada
• Valores e coberturas
• Condições especiais

Aguarde alguns instantes... 🔄""",
            
            'error': """😅 *Ops! Algo deu errado...*

Não consegui processar sua mensagem corretamente. Pode tentar novamente?

Se preferir, pode enviar as informações do seu animal de forma mais simples, como:
"Nome: Relâmpago, Valor: R$ 50.000, Raça: Quarto de Milha"

Estou aqui para ajudar! 🤝"""
        }
    
    def extract_animal_data(self, message: str, existing_data: Dict = None) -> Dict:
        """Extrai dados do animal da mensagem usando IA"""
        try:
            if not self.openai_api_key:
                return self._extract_data_simple(message, existing_data)
            
            # Dados existentes para contexto
            existing_context = ""
            if existing_data:
                existing_context = "\nDados já coletados: " + json.dumps(existing_data, ensure_ascii=False)

            system_text = """
            Você é um assistente educado, amigável e objetivo.
            Tem a função de coletar dados para seguros de equinos.
            Explique claramente se precisar pedir informações adicionais.
            Jamais invente dados.
            Se não encontrar alguma informação obrigatória, deixe o campo vazio.

            Campos obrigatórios:
            - nome_solicitante
            - cpf_solicitante
            - nome_animal
            - valor_animal
            - raca
            - data_nascimento
            - sexo
            - utilizacao
            - rua
            - numero
            - bairro
            - cidade
            - uf
            - cep

            No retorno, além dos dados acima, inclua também:
            "dados_completos": true  → se todos os campos estiverem preenchidos
            "dados_completos": false → se faltar pelo menos um campo

            Responda APENAS com um JSON válido. Exemplo:
            {
            "nome_solicitante": "João",
            "cpf_solicitante": "12345678900",
            "nome_animal": "Mancha",
            "valor_animal": "10000",
            "raca": "Mangalarga",
            "data_nascimento": "21/04/2023",
            "sexo": "inteiro",
            "utilizacao": "lazer",
            "rua": "Rua Exemplo",
            "numero": "123",
            "bairro": "Centro",
            "cidade": "Campinas",
            "uf": "SP",
            "cep": "13058000",
            "dados_completos": true
            }
            """ + existing_context
            
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_text},
                    {"role": "user", "content": message},
                ],
                max_tokens=200,
                temperature=0.1,
            )
            
            # Tentar extrair JSON da resposta
            response_text = response.choices[0].message.content.strip()
            
            # Limpar resposta para extrair apenas JSON
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                extracted_data = json.loads(json_str)
                # mescla com o que já tinha
                base = (existing_data or {}).copy()
                base.update(extracted_data)

                # valida / normaliza
                normalizado, faltantes = normaliza_e_valida(base)
                return normalizado
            else:
                return existing_data or {}
                
        except Exception as e:
            logger.error(f"Erro na extração de dados com IA: {str(e)}")
            return self._extract_data_simple(message, existing_data)
    
    def _extract_data_simple(self, message: str, existing_data: Dict = None) -> Dict:
        """Extração simples de dados sem IA"""
        data = existing_data.copy() if existing_data else {}
        message_lower = message.lower()
        
        # Padrões simples de extração
        patterns = {
            'nome_animal': [r'nome[:\s]+([a-záàâãéêíóôõúç\s]+)', r'chama[:\s]+([a-záàâãéêíóôõúç\s]+)'],
            'valor_animal': [r'valor[:\s]*r?\$?\s*([0-9.,]+)', r'vale[:\s]*r?\$?\s*([0-9.,]+)'],
            'raca': [r'raça[:\s]+([a-záàâãéêíóôõúç\s]+)', r'é\s+um[a]?\s+([a-záàâãéêíóôõúç\s]+)'],
            'sexo': [r'(inteiro|castrado|fêmea|macho|égua)'],
            'utilizacao': [r'(lazer|salto|laço|corrida|trabalho|esporte)']
        }
        
        for field, pattern_list in patterns.items():
            if field not in data or not data[field]:
                for pattern in pattern_list:
                    match = re.search(pattern, message_lower)
                    if match:
                        data[field] = match.group(1).strip()
                        break
        
        return data
    
    def generate_response(self, phone: str, message: str, client_data: Dict, conversation_count: int) -> str:
        """Gera resposta baseada no contexto"""
        try:
            # Primeira mensagem - saudação
            if conversation_count == 0:
                return self.templates['welcome']
            
            # Extrair dados da mensagem atual
            existing_data = client_data.get('data', {})
            updated_data = self.extract_animal_data(message, existing_data)
            
            if updated_data.get("dados_completos"):
                # monte o resumo e siga pro fluxo SwissRe
                complete_data = "\n".join([f"✅ {k}: {updated_data[k]}" for k in
                    ["nome","cpf","rua","numero","bairro","cidade","uf","cep","valor"]])
                return self.templates['complete_data'].format(complete_data=complete_data)
            else:
                # liste apenas os que faltam, com rótulos amigáveis
                obrigatorios_pt = {
                "nome":"Nome Solicitante","cpf":"CPF Solicitante","valor":"Valor do Animal (R$)",
                "rua":"Rua","numero":"Número","bairro":"Bairro","cidade":"Cidade","uf":"uf","cep":"CEP"
                }
                _, faltantes = normaliza_e_valida(updated_data)
                missing = "\n".join(f"❌ {obrigatorios_pt[c]}" for c in faltantes)
                collected = "\n".join(f"✅ {obrigatorios_pt.get(k,k)}: {v}"
                                    for k,v in updated_data.items() if k in obrigatorios_pt and v)
                return self.templates['partial_data'].format(
                    collected_data= collected or "Nenhum dado coletado ainda.",
                    missing_data= missing
                )

        except Exception as e:
            logger.error(f"Erro ao gerar resposta: {str(e)}")
            return self.templates['error']
    
    def _generate_helpful_response(self, message: str) -> str:
        """Gera resposta útil quando não consegue extrair dados"""
        message_lower = message.lower()
        
        # Respostas baseadas em palavras-chave
        if any(word in message_lower for word in ['oi', 'olá', 'bom dia', 'boa tarde', 'boa noite']):
            return """😊 *Olá! Que bom te ver aqui!*

Vou te ajudar com a cotação do seguro do seu equino.

Para começar, pode me falar:
• Qual o nome do seu animal?
• Qual o valor aproximado dele?

Ou se preferir, pode enviar todas as informações de uma vez! 🐴"""
        
        elif any(word in message_lower for word in ['ajuda', 'help', 'como', 'não sei']):
            return """🤝 *Claro! Vou te ajudar!*

É bem simples! Preciso de algumas informações sobre seu equino:

📝 *Pode enviar assim:*
"Nome: Relâmpago
Valor: R$ 50.000
Raça: Quarto de Milha
Sexo: Inteiro
Uso: Lazer"

Ou pode ir enviando uma informação por vez. Como preferir! 😊"""
        
        elif any(word in message_lower for word in ['cotação', 'seguro', 'preço']):
            return """💰 *Perfeito! Vamos fazer sua cotação!*

Para calcular o valor do seguro, preciso conhecer melhor seu animal.

Pode começar me contando:
• Nome do animal
• Valor dele
• Que raça é

Vou organizando tudo para você! 📋"""
        
        else:
            return """📝 *Obrigado pela mensagem!*

Para te ajudar melhor com a cotação, pode me enviar as informações do seu animal?

*Exemplos:*
• "Meu cavalo se chama Thor, vale R$ 80.000"
• "É uma égua Mangalarga, uso para lazer"
• "Registro: 12345, nasceu em 15/03/2018"

Qualquer formato está bom! Vou entender e organizar para você. 😊"""
    
    def format_final_summary(self, client_data: Dict) -> str:
        """Formata resumo final dos dados coletados"""
        try:
            data = client_data.get('data', {})
            
            summary_lines = []
            if data.get('nome_animal'):
                summary_lines.append(f"🐴 *Animal:* {data['nome_animal']}")
            if data.get('valor_animal'):
                summary_lines.append(f"💰 *Valor:* R$ {data['valor_animal']}")
            if data.get('raca'):
                summary_lines.append(f"🏇 *Raça:* {data['raca']}")
            if data.get('sexo'):
                summary_lines.append(f"⚥ *Sexo:* {data['sexo']}")
            if data.get('data_nascimento'):
                summary_lines.append(f"📅 *Nascimento:* {data['data_nascimento']}")
            if data.get('utilizacao'):
                summary_lines.append(f"🎯 *Uso:* {data['utilizacao']}")
            if data.get('registro'):
                summary_lines.append(f"📋 *Registro:* {data['registro']}")
            if data.get('endereco'):
                summary_lines.append(f"📍 *Cocheira:* {data['endereco']}")
            
            summary = "\\n".join(summary_lines)
            
            return f"""✅ *DADOS COLETADOS COM SUCESSO!*

{summary}

🎉 *Cotação em processamento...*

Sua proposta personalizada será gerada em instantes!"""
        
        except Exception as e:
            logger.error(f"Erro ao formatar resumo: {str(e)}")
            return "✅ Dados coletados! Processando cotação..."

# Instância global do gerador
response_generator = ResponseGenerator()

