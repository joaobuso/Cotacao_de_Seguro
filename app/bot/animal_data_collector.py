# -*- coding: utf-8 -*-
"""
Coletor de dados do animal para cotação de seguro
"""

import re
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class AnimalDataCollector:
    """
    Classe para coletar e validar dados do animal
    """
    
    # Campos obrigatórios
    REQUIRED_FIELDS = {
        'nome_animal': 'Nome do Animal',
        'valor_animal': 'Valor do Animal',
        'registro_passaporte': 'Número de Registro/Passaporte',
        'raca': 'Raça',
        'data_nascimento': 'Data de Nascimento',
        'sexo': 'Sexo',
        'utilizacao': 'Utilização',
        'endereco_cocheira': 'Endereço da Cocheira'
    }
    
    def __init__(self, phone_number: str):
        self.phone_number = phone_number
        self.data = {}
        self._load_existing_data()
    
    def _load_existing_data(self):
        """
        Carrega dados existentes do usuário (implementar com banco de dados)
        """
        # Por enquanto, dados vazios
        # TODO: Implementar carregamento do banco de dados
        pass
    
    def extract_and_update_data(self, message: str) -> List[str]:
        """
        Extrai dados da mensagem e atualiza campos
        
        Args:
            message: Mensagem do usuário
            
        Returns:
            Lista de campos atualizados
        """
        updated_fields = []
        message_lower = message.lower()
        
        # Extrair nome do animal
        nome_patterns = [
            r'nome.*?(?:é|:)\s*([a-záàâãéèêíìîóòôõúùûç\s]+)',
            r'chama.*?(?:se|:)\s*([a-záàâãéèêíìîóòôõúùûç\s]+)',
            r'animal.*?(?:é|:)\s*([a-záàâãéèêíìîóòôõúùûç\s]+)'
        ]
        
        for pattern in nome_patterns:
            match = re.search(pattern, message_lower)
            if match:
                nome = match.group(1).strip().title()
                if len(nome) > 2 and not nome.isdigit():
                    self.data['nome_animal'] = nome
                    updated_fields.append('nome_animal')
                    break
        
        # Extrair valor do animal
        valor_patterns = [
            r'valor.*?(?:é|:)?\s*r?\$?\s*([\d.,]+)',
            r'vale.*?r?\$?\s*([\d.,]+)',
            r'custa.*?r?\$?\s*([\d.,]+)',
            r'r?\$\s*([\d.,]+)'
        ]
        
        for pattern in valor_patterns:
            match = re.search(pattern, message_lower)
            if match:
                valor_str = match.group(1).replace('.', '').replace(',', '.')
                try:
                    valor = float(valor_str)
                    if valor > 0:
                        self.data['valor_animal'] = f"R$ {valor:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
                        updated_fields.append('valor_animal')
                        break
                except ValueError:
                    continue
        
        # Extrair registro/passaporte
        registro_patterns = [
            r'registro.*?(?:é|:)?\s*([a-z0-9\-]+)',
            r'passaporte.*?(?:é|:)?\s*([a-z0-9\-]+)',
            r'número.*?(?:é|:)?\s*([a-z0-9\-]+)'
        ]
        
        for pattern in registro_patterns:
            match = re.search(pattern, message_lower)
            if match:
                registro = match.group(1).strip().upper()
                if len(registro) > 2:
                    self.data['registro_passaporte'] = registro
                    updated_fields.append('registro_passaporte')
                    break
        
        # Extrair raça
        racas_conhecidas = [
            'quarto de milha', 'puro sangue inglês', 'mangalarga', 'crioulo', 
            'andaluz', 'árabe', 'appaloosa', 'paint horse', 'campolina',
            'brasileiro de hipismo', 'lusitano', 'friesian', 'clydesdale'
        ]
        
        raca_patterns = [
            r'raça.*?(?:é|:)?\s*([a-záàâãéèêíìîóòôõúùûç\s]+)',
            r'é.*?(?:da raça|raça)\s*([a-záàâãéèêíìîóòôõúùûç\s]+)'
        ]
        
        for pattern in raca_patterns:
            match = re.search(pattern, message_lower)
            if match:
                raca = match.group(1).strip()
                # Verificar se é uma raça conhecida ou pelo menos tem mais de 3 caracteres
                if any(r in raca for r in racas_conhecidas) or len(raca) > 3:
                    self.data['raca'] = raca.title()
                    updated_fields.append('raca')
                    break
        
        # Extrair data de nascimento
        data_patterns = [
            r'nasceu.*?(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{4})',
            r'nascimento.*?(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{4})',
            r'data.*?(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{4})',
            r'(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{4})'
        ]
        
        for pattern in data_patterns:
            match = re.search(pattern, message)
            if match:
                data_str = match.group(1)
                try:
                    # Tentar diferentes formatos
                    for fmt in ['%d/%m/%Y', '%d-%m-%Y']:
                        try:
                            data_obj = datetime.strptime(data_str, fmt)
                            if 1990 <= data_obj.year <= datetime.now().year:
                                self.data['data_nascimento'] = data_obj.strftime('%d/%m/%Y')
                                updated_fields.append('data_nascimento')
                                break
                        except ValueError:
                            continue
                    if 'data_nascimento' in updated_fields:
                        break
                except:
                    continue
        
        # Extrair sexo
        if any(word in message_lower for word in ['macho', 'inteiro', 'garanhão']):
            self.data['sexo'] = 'Macho/Inteiro'
            updated_fields.append('sexo')
        elif any(word in message_lower for word in ['castrado', 'capado']):
            self.data['sexo'] = 'Castrado'
            updated_fields.append('sexo')
        elif any(word in message_lower for word in ['fêmea', 'égua', 'potra']):
            self.data['sexo'] = 'Fêmea'
            updated_fields.append('sexo')
        
        # Extrair utilização
        utilizacoes = {
            'lazer': ['lazer', 'passeio', 'recreação'],
            'salto': ['salto', 'hipismo', 'obstáculo'],
            'laço': ['laço', 'rodeio', 'vaquejada'],
            'corrida': ['corrida', 'turfe', 'galope'],
            'adestramento': ['adestramento', 'dressage'],
            'reprodução': ['reprodução', 'cobertura', 'monta']
        }
        
        for uso, keywords in utilizacoes.items():
            if any(keyword in message_lower for keyword in keywords):
                self.data['utilizacao'] = uso.title()
                updated_fields.append('utilizacao')
                break
        
        # Extrair endereço/CEP
        cep_pattern = r'(\d{5}[-]?\d{3})'
        cep_match = re.search(cep_pattern, message)
        if cep_match:
            cep = cep_match.group(1)
            if '-' not in cep:
                cep = f"{cep[:5]}-{cep[5:]}"
            
            # Extrair cidade se mencionada
            cidade_patterns = [
                r'(?:cidade|em|de)\s*([a-záàâãéèêíìîóòôõúùûç\s]+)',
                r'([a-záàâãéèêíìîóòôõúùûç\s]+)\s*[-,]\s*[a-z]{2}'
            ]
            
            cidade = ""
            for pattern in cidade_patterns:
                match = re.search(pattern, message_lower)
                if match:
                    cidade = match.group(1).strip().title()
                    break
            
            endereco = f"CEP: {cep}"
            if cidade:
                endereco += f", {cidade}"
            
            self.data['endereco_cocheira'] = endereco
            updated_fields.append('endereco_cocheira')
        
        return updated_fields
    
    def is_complete(self) -> bool:
        """
        Verifica se todos os dados obrigatórios foram coletados
        """
        return all(field in self.data and self.data[field] for field in self.REQUIRED_FIELDS.keys())
    
    def get_missing_fields(self) -> List[str]:
        """
        Retorna lista de campos faltantes
        """
        return [field for field in self.REQUIRED_FIELDS.keys() if field not in self.data or not self.data[field]]
    
    def get_summary(self) -> str:
        """
        Retorna resumo dos dados coletados
        """
        if not self.data:
            return "Nenhum dado coletado ainda."
        
        summary_lines = []
        for field, value in self.data.items():
            if value:
                field_name = self.REQUIRED_FIELDS.get(field, field)
                summary_lines.append(f"• **{field_name}:** {value}")
        
        return "\n".join(summary_lines)
    
    def get_formatted_data_for_swissre(self) -> Dict[str, Any]:
        """
        Retorna dados formatados para o sistema SwissRe
        """
        return {
            'nome_animal': self.data.get('nome_animal', ''),
            'valor_animal': self.data.get('valor_animal', ''),
            'registro_passaporte': self.data.get('registro_passaporte', ''),
            'raca': self.data.get('raca', ''),
            'data_nascimento': self.data.get('data_nascimento', ''),
            'sexo': self.data.get('sexo', ''),
            'utilizacao': self.data.get('utilizacao', ''),
            'endereco_cocheira': self.data.get('endereco_cocheira', ''),
            'phone_number': self.phone_number,
            'timestamp': datetime.now().isoformat()
        }
    
    def save_data(self, conversation_id: str):
        """
        Salva dados no banco de dados
        
        Args:
            conversation_id: ID da conversa
        """
        try:
            # TODO: Implementar salvamento no banco de dados
            logger.info(f"Dados salvos para conversa {conversation_id}: {len(self.data)} campos")
        except Exception as e:
            logger.error(f"Erro ao salvar dados: {str(e)}")
    
    def to_json(self) -> str:
        """
        Converte dados para JSON
        """
        return json.dumps(self.data, ensure_ascii=False, indent=2)

