import re
from datetime import datetime
from ..db import database

class AnimalDataCollector:
    """
    Classe para coletar e validar dados obrigatórios do animal para cotação de seguro.
    """
    
    # Campos obrigatórios para cotação
    REQUIRED_FIELDS = {
        'nome_animal': 'Nome do Animal',
        'valor_animal': 'Valor do Animal',
        'registro_passaporte': 'Número de Registro ou Passaporte',
        'raca': 'Raça',
        'data_nascimento': 'Data de Nascimento',
        'sexo': 'Sexo (inteiro, castrado ou fêmea)',
        'utilizacao': 'Utilização (lazer, salto, laço etc.)',
        'endereco_cocheira': 'Endereço da Cocheira (CEP e cidade)'
    }
    
    # Opções válidas para sexo
    SEXO_OPTIONS = ['inteiro', 'castrado', 'fêmea', 'femea']
    
    def __init__(self, phone_number):
        self.phone_number = phone_number
        self.data = self.load_existing_data()
    
    def load_existing_data(self):
        """Carrega dados existentes do banco de dados."""
        try:
            # Buscar dados existentes no banco
            conversation_status, conversation_id = database.get_conversation_status_and_id(self.phone_number)
            if conversation_id:
                conversation = database.get_conversation_by_id(str(conversation_id))
                if conversation and 'animal_data' in conversation:
                    return conversation['animal_data']
            return {}
        except Exception as e:
            print(f"Erro ao carregar dados existentes: {e}")
            return {}
    
    def save_data(self, conversation_id):
        """Salva os dados no banco de dados."""
        try:
            if isinstance(conversation_id, str):
                from bson import ObjectId
                conversation_id = ObjectId(conversation_id)
            
            database.conversations_collection.update_one(
                {"_id": conversation_id},
                {"$set": {"animal_data": self.data, "updated_at": datetime.now()}}
            )
            return True
        except Exception as e:
            print(f"Erro ao salvar dados do animal: {e}")
            return False
    
    def extract_and_update_data(self, message_text):
        """
        Extrai informações do animal da mensagem e atualiza os dados.
        Retorna uma lista de campos que foram atualizados.
        """
        updated_fields = []
        message_lower = message_text.lower()
        
        # Extrair nome do animal
        if not self.data.get('nome_animal'):
            nome_patterns = [
                r'nome(?:\s+do\s+animal)?[:\s]+([a-zA-Z\s]+)',
                r'animal[:\s]+([a-zA-Z\s]+)',
                r'chama[:\s]+([a-zA-Z\s]+)',
                r'nome[:\s]+([a-zA-Z\s]+)'
            ]
            for pattern in nome_patterns:
                match = re.search(pattern, message_lower)
                if match:
                    nome = match.group(1).strip().title()
                    if len(nome) > 2:  # Nome deve ter pelo menos 3 caracteres
                        self.data['nome_animal'] = nome
                        updated_fields.append('nome_animal')
                        break
        
        # Extrair valor do animal
        if not self.data.get('valor_animal'):
            valor_patterns = [
                r'valor(?:\s+do\s+animal)?[:\s]*r?\$?\s*([0-9.,]+)',
                r'vale[:\s]*r?\$?\s*([0-9.,]+)',
                r'custa[:\s]*r?\$?\s*([0-9.,]+)',
                r'pre[çc]o[:\s]*r?\$?\s*([0-9.,]+)'
            ]
            for pattern in valor_patterns:
                match = re.search(pattern, message_lower)
                if match:
                    valor = match.group(1).replace(',', '.')
                    try:
                        valor_float = float(valor)
                        if valor_float > 0:
                            self.data['valor_animal'] = f"R$ {valor_float:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
                            updated_fields.append('valor_animal')
                            break
                    except ValueError:
                        continue
        
        # Extrair registro/passaporte
        if not self.data.get('registro_passaporte'):
            registro_patterns = [
                r'registro[:\s]+([a-zA-Z0-9]+)',
                r'passaporte[:\s]+([a-zA-Z0-9]+)',
                r'n[úu]mero[:\s]+([a-zA-Z0-9]+)',
                r'documento[:\s]+([a-zA-Z0-9]+)'
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
        if not self.data.get('raca'):
            raca_patterns = [
                r'ra[çc]a[:\s]+([a-zA-Z\s]+)',
                r'[éeE]\s+um[a]?\s+([a-zA-Z\s]+)',
                r'tipo[:\s]+([a-zA-Z\s]+)'
            ]
            for pattern in raca_patterns:
                match = re.search(pattern, message_lower)
                if match:
                    raca = match.group(1).strip().title()
                    if len(raca) > 2:
                        self.data['raca'] = raca
                        updated_fields.append('raca')
                        break
        
        # Extrair data de nascimento
        if not self.data.get('data_nascimento'):
            data_patterns = [
                r'nasceu[:\s]+(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{4})',
                r'nascimento[:\s]+(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{4})',
                r'data[:\s]+(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{4})',
                r'(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{4})'
            ]
            for pattern in data_patterns:
                match = re.search(pattern, message_text)
                if match:
                    data_str = match.group(1)
                    try:
                        # Tentar diferentes formatos de data
                        for fmt in ['%d/%m/%Y', '%d-%m-%Y', '%m/%d/%Y', '%m-%d-%Y']:
                            try:
                                data_obj = datetime.strptime(data_str, fmt)
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
        if not self.data.get('sexo'):
            for sexo_option in self.SEXO_OPTIONS:
                if sexo_option in message_lower:
                    self.data['sexo'] = sexo_option.title()
                    updated_fields.append('sexo')
                    break
        
        # Extrair utilização
        if not self.data.get('utilizacao'):
            utilizacao_patterns = [
                r'utiliza[çc][ãa]o[:\s]+([a-zA-Z\s,]+)',
                r'usa(?:do)?\s+para[:\s]+([a-zA-Z\s,]+)',
                r'finalidade[:\s]+([a-zA-Z\s,]+)',
                r'atividade[:\s]+([a-zA-Z\s,]+)'
            ]
            for pattern in utilizacao_patterns:
                match = re.search(pattern, message_lower)
                if match:
                    utilizacao = match.group(1).strip().title()
                    if len(utilizacao) > 2:
                        self.data['utilizacao'] = utilizacao
                        updated_fields.append('utilizacao')
                        break
        
        # Extrair endereço da cocheira
        if not self.data.get('endereco_cocheira'):
            endereco_patterns = [
                r'cocheira[:\s]+([^.]+)',
                r'endere[çc]o[:\s]+([^.]+)',
                r'fica(?:\s+em)?[:\s]+([^.]+)',
                r'localiza[çc][ãa]o[:\s]+([^.]+)',
                r'cep[:\s]+(\d{5}-?\d{3}[^.]*)'
            ]
            for pattern in endereco_patterns:
                match = re.search(pattern, message_lower)
                if match:
                    endereco = match.group(1).strip().title()
                    if len(endereco) > 5:
                        self.data['endereco_cocheira'] = endereco
                        updated_fields.append('endereco_cocheira')
                        break
        
        return updated_fields
    
    def get_missing_fields(self):
        """Retorna uma lista dos campos obrigatórios que ainda não foram preenchidos."""
        missing = []
        for field_key, field_name in self.REQUIRED_FIELDS.items():
            if not self.data.get(field_key):
                missing.append(field_name)
        return missing
    
    def is_complete(self):
        """Verifica se todos os campos obrigatórios foram preenchidos."""
        return len(self.get_missing_fields()) == 0
    
    def get_summary(self):
        """Retorna um resumo formatado dos dados coletados."""
        if not self.data:
            return "Nenhum dado foi coletado ainda."
        
        summary = "📋 **Dados coletados até agora:**\n\n"
        for field_key, field_name in self.REQUIRED_FIELDS.items():
            value = self.data.get(field_key, "❌ Não informado")
            summary += f"• **{field_name}:** {value}\n"
        
        missing = self.get_missing_fields()
        if missing:
            summary += f"\n⚠️ **Ainda faltam:** {', '.join(missing)}"
        else:
            summary += "\n✅ **Todos os dados foram coletados!**"
        
        return summary
    
    def get_formatted_data_for_swissre(self):
        """Retorna os dados formatados para uso no script swissre.py."""
        if not self.is_complete():
            return None
        
        return {
            'nome_animal': self.data['nome_animal'],
            'valor_animal': self.data['valor_animal'],
            'registro_passaporte': self.data['registro_passaporte'],
            'raca': self.data['raca'],
            'data_nascimento': self.data['data_nascimento'],
            'sexo': self.data['sexo'],
            'utilizacao': self.data['utilizacao'],
            'endereco_cocheira': self.data['endereco_cocheira']
        }

