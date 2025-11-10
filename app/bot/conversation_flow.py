# -*- coding: utf-8 -*-
"""
Sistema Centralizado de Fluxo de Conversação
Gerencia estados, transições e templates de mensagens em um único local
"""

from enum import Enum
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class ConversationState(Enum):
    """Estados possíveis da conversa"""
    INITIAL = "initial"                    # Estado inicial - primeira interação
    MENU_PRINCIPAL = "menu_principal"      # Menu de escolha de atendimento
    INFO_EMPRESA = "info_empresa"          # Informações sobre a empresa
    COTACAO_INICIO = "cotacao_inicio"      # Início do processo de cotação
    COTACAO_COLETANDO = "cotacao_coletando"  # Coletando dados para cotação
    COTACAO_VALIDANDO = "cotacao_validando"  # Validando dados coletados
    COTACAO_PROCESSANDO = "cotacao_processando"  # Processando cotação
    COTACAO_CONCLUIDA = "cotacao_concluida"  # Cotação finalizada
    POS_COTACAO = "pos_cotacao"            # Após cotação - oferecer mais opções
    AGUARDANDO_ATENDENTE = "aguardando_atendente"  # Solicitou atendente humano
    ATENDENTE_ATIVO = "atendente_ativo"    # Atendente humano assumiu
    ENCERRADA = "encerrada"                # Conversa encerrada


class MessageTemplate:
    """Templates de mensagens organizados por estado"""
    
    TEMPLATES = {
        # Mensagem inicial de apresentação
        ConversationState.INITIAL: """🐴 *Olá! Bem-vindo à Equinos Seguros!*

Sou seu assistente virtual e estou aqui para ajudá-lo da melhor forma possível.

*Como posso te ajudar hoje?*

Digite o número da opção desejada:

*1* - Saber mais sobre a Equinos Seguros
*2* - Realizar Cotação de Seguro

_Você também pode digitar "atendente" a qualquer momento para falar com um humano._""",

        # Informações sobre a empresa
        ConversationState.INFO_EMPRESA: """📋 *Sobre a Equinos Seguros*

{info_empresa_texto}

*Deseja realizar uma cotação de seguro agora?*

Digite:
*1* - Sim, quero fazer uma cotação
*2* - Não, obrigado

Ou digite "menu" para voltar ao menu principal.""",

        # Início da cotação
        ConversationState.COTACAO_INICIO: """✅ *Ótimo! Vamos iniciar sua cotação de seguro.*

Para gerar uma cotação personalizada, preciso coletar algumas informações sobre você e seu animal.

📋 *DADOS NECESSÁRIOS:*

*Dados do Solicitante:*
• Nome Completo
• CPF

*Dados do Animal:*
• Nome do Animal
• Valor do Animal (R$)
• Raça
• Data de Nascimento (DD/MM/AAAA)
• Sexo (inteiro, castrado ou fêmea)
• Utilização (lazer, salto, laço, etc.)

*Endereço da Cocheira:*
• Rua
• Número
• Bairro
• Cidade
• UF
• CEP

Você pode enviar todas as informações de uma vez ou ir enviando aos poucos. Vou organizando tudo para você! 😊

*Pode começar enviando as informações.*""",

        # Coletando dados
        ConversationState.COTACAO_COLETANDO: """📝 *Obrigado pelas informações!*

*DADOS JÁ COLETADOS:*
{dados_coletados}

*AINDA PRECISO DE:*
{dados_faltantes}

Por favor, envie as informações que ainda faltam. Estou aqui para ajudar! 😊

_Digite "atendente" se precisar de ajuda humana._""",

        # Validando dados completos
        ConversationState.COTACAO_VALIDANDO: """✅ *Perfeito! Coletei todas as informações necessárias.*

*RESUMO DOS DADOS:*
{resumo_completo}

*Está tudo correto?*

Digite:
*1* - Sim, processar cotação
*2* - Não, preciso corrigir algo

_Se precisar corrigir, basta me dizer qual informação está errada._""",

        # Processando cotação
        ConversationState.COTACAO_PROCESSANDO: """🔄 *Processando sua cotação...*

Estou enviando seus dados para o sistema da seguradora e gerando sua proposta personalizada.

⏳ *Isso pode levar alguns minutos.*

📄 Assim que a cotação estiver pronta, enviarei o documento PDF com todos os detalhes.

_Por favor, aguarde..._""",

        # Cotação concluída com sucesso
        ConversationState.COTACAO_CONCLUIDA: """✅ *Cotação realizada com sucesso!*

📄 Sua proposta de seguro foi gerada e está sendo enviada agora.

{mensagem_resultado}

*Deseja mais alguma informação?*

Digite:
*1* - Fazer nova cotação
*2* - Falar com atendente
*3* - Encerrar atendimento""",

        # Após cotação - menu de opções
        ConversationState.POS_COTACAO: """🤝 *Como posso ajudar mais?*

Digite o número da opção desejada:

*1* - Fazer nova cotação
*2* - Informações sobre a empresa
*3* - Falar com atendente humano
*4* - Encerrar atendimento""",

        # Aguardando atendente
        ConversationState.AGUARDANDO_ATENDENTE: """👤 *Transferindo para atendente humano...*

Entendi que você gostaria de falar com um atendente humano.

Um de nossos agentes irá assumir esta conversa em breve.

⏳ *Por favor, aguarde um momento.*

_Suas mensagens estão sendo registradas e o atendente verá todo o histórico da conversa._""",

        # Atendente ativo
        ConversationState.ATENDENTE_ATIVO: """👤 *Atendente humano conectado*

Um de nossos agentes assumiu esta conversa e irá responder suas mensagens.

_Continue enviando suas dúvidas que o atendente irá ajudá-lo._""",

        # Conversa encerrada
        ConversationState.ENCERRADA: """👋 *Obrigado por usar a Equinos Seguros!*

Foi um prazer atendê-lo.

Se precisar de qualquer coisa, é só enviar uma mensagem que estarei aqui para ajudar!

🐴 *Até logo!*"""
    }

    @staticmethod
    def get_template(state: ConversationState) -> str:
        """Retorna o template para o estado especificado"""
        return MessageTemplate.TEMPLATES.get(state, "")

    @staticmethod
    def format_template(state: ConversationState, **kwargs) -> str:
        """Formata o template com os dados fornecidos"""
        template = MessageTemplate.get_template(state)
        try:
            return template.format(**kwargs)
        except KeyError as e:
            logger.error(f"Erro ao formatar template: campo {e} não fornecido")
            return template


class ConversationFlow:
    """
    Gerenciador central do fluxo de conversação
    Controla estados, transições e lógica de negócio
    """
    
    # Campos obrigatórios para cotação
    REQUIRED_FIELDS = {
        'nome_solicitante': 'Nome do Solicitante',
        'cpf_solicitante': 'CPF do Solicitante',
        'nome_animal': 'Nome do Animal',
        'valor_animal': 'Valor do Animal',
        'raca': 'Raça',
        'data_nascimento': 'Data de Nascimento',
        'sexo': 'Sexo',
        'utilizacao': 'Utilização',
        'rua': 'Rua',
        'numero': 'Número',
        'bairro': 'Bairro',
        'cidade': 'Cidade',
        'uf': 'UF',
        'cep': 'CEP'
    }
    
    # Tempo de expiração da conversa (10 minutos)
    CONVERSATION_TIMEOUT = timedelta(minutes=10)
    
    # Tempo para reativar bot após atendente (24 horas)
    AGENT_TIMEOUT = timedelta(hours=24)
    
    def __init__(self):
        """Inicializa o gerenciador de fluxo"""
        self.conversations = {}  # Armazena estado de cada conversa
    
    def get_conversation_state(self, phone: str) -> ConversationState:
        """Retorna o estado atual da conversa"""
        if phone not in self.conversations:
            return ConversationState.INITIAL
        
        conv = self.conversations[phone]
        
        # Verificar timeout da conversa
        last_interaction = conv.get('last_interaction')
        if last_interaction:
            time_diff = datetime.now() - last_interaction
            
            # Se passou mais de 10 minutos, resetar para inicial
            if time_diff > self.CONVERSATION_TIMEOUT:
                logger.info(f"Conversa expirada para {phone}, resetando para INITIAL")
                self.reset_conversation(phone)
                return ConversationState.INITIAL
            
            # Se está com atendente e passou 24h sem interação, reativar bot
            if conv['state'] == ConversationState.ATENDENTE_ATIVO:
                if time_diff > self.AGENT_TIMEOUT:
                    logger.info(f"Timeout de atendente para {phone}, reativando bot")
                    self.reset_conversation(phone)
                    return ConversationState.INITIAL
        
        return conv['state']
    
    def set_conversation_state(self, phone: str, state: ConversationState):
        """Define o estado da conversa"""
        if phone not in self.conversations:
            self.conversations[phone] = {
                'state': state,
                'data': {},
                'created_at': datetime.now(),
                'last_interaction': datetime.now(),
                'message_count': 0,
                'cotacoes_realizadas': []
            }
        else:
            self.conversations[phone]['state'] = state
            self.conversations[phone]['last_interaction'] = datetime.now()
    
    def update_conversation_data(self, phone: str, data: Dict):
        """Atualiza os dados da conversa"""
        if phone not in self.conversations:
            self.conversations[phone] = {
                'state': ConversationState.INITIAL,
                'data': {},
                'created_at': datetime.now(),
                'last_interaction': datetime.now(),
                'message_count': 0,
                'cotacoes_realizadas': []
            }
        
        self.conversations[phone]['data'].update(data)
        self.conversations[phone]['last_interaction'] = datetime.now()
        self.conversations[phone]['message_count'] += 1
    
    def get_conversation_data(self, phone: str) -> Dict:
        """Retorna os dados da conversa"""
        if phone not in self.conversations:
            return {}
        return self.conversations[phone]['data']
    
    def reset_conversation(self, phone: str):
        """Reseta a conversa para o estado inicial"""
        if phone in self.conversations:
            # Preservar histórico de cotações
            cotacoes = self.conversations[phone].get('cotacoes_realizadas', [])
            self.conversations[phone] = {
                'state': ConversationState.INITIAL,
                'data': {},
                'created_at': datetime.now(),
                'last_interaction': datetime.now(),
                'message_count': 0,
                'cotacoes_realizadas': cotacoes
            }
    
    def add_cotacao_realizada(self, phone: str, cotacao_data: Dict):
        """Adiciona uma cotação ao histórico"""
        if phone not in self.conversations:
            return
        
        if 'cotacoes_realizadas' not in self.conversations[phone]:
            self.conversations[phone]['cotacoes_realizadas'] = []
        
        cotacao_data['timestamp'] = datetime.now().isoformat()
        self.conversations[phone]['cotacoes_realizadas'].append(cotacao_data)
    
    def get_missing_fields(self, phone: str) -> List[str]:
        """Retorna lista de campos obrigatórios que ainda faltam"""
        data = self.get_conversation_data(phone)
        missing = []
        
        for field_key, field_name in self.REQUIRED_FIELDS.items():
            if field_key not in data or not data[field_key]:
                missing.append(field_name)
        
        return missing
    
    def is_data_complete(self, phone: str) -> bool:
        """Verifica se todos os dados obrigatórios foram coletados"""
        return len(self.get_missing_fields(phone)) == 0
    
    def format_collected_data(self, phone: str) -> str:
        """Formata os dados já coletados para exibição"""
        data = self.get_conversation_data(phone)
        lines = []
        
        for field_key, field_name in self.REQUIRED_FIELDS.items():
            if field_key in data and data[field_key]:
                lines.append(f"✅ {field_name}: {data[field_key]}")
        
        return "\n".join(lines) if lines else "Nenhum dado coletado ainda."
    
    def format_missing_data(self, phone: str) -> str:
        """Formata os dados faltantes para exibição"""
        missing = self.get_missing_fields(phone)
        if not missing:
            return "Todos os dados foram coletados! ✅"
        
        return "\n".join([f"❌ {field}" for field in missing])
    
    def format_complete_summary(self, phone: str) -> str:
        """Formata resumo completo dos dados para validação"""
        data = self.get_conversation_data(phone)
        lines = []
        
        lines.append("*Dados do Solicitante:*")
        lines.append(f"• Nome: {data.get('nome_solicitante', 'N/A')}")
        lines.append(f"• CPF: {data.get('cpf_solicitante', 'N/A')}")
        lines.append("")
        
        lines.append("*Dados do Animal:*")
        lines.append(f"• Nome: {data.get('nome_animal', 'N/A')}")
        lines.append(f"• Valor: R$ {data.get('valor_animal', 'N/A')}")
        lines.append(f"• Raça: {data.get('raca', 'N/A')}")
        lines.append(f"• Data de Nascimento: {data.get('data_nascimento', 'N/A')}")
        lines.append(f"• Sexo: {data.get('sexo', 'N/A')}")
        lines.append(f"• Utilização: {data.get('utilizacao', 'N/A')}")
        lines.append("")
        
        lines.append("*Endereço da Cocheira:*")
        lines.append(f"• {data.get('rua', 'N/A')}, {data.get('numero', 'N/A')}")
        lines.append(f"• {data.get('bairro', 'N/A')}")
        lines.append(f"• {data.get('cidade', 'N/A')} - {data.get('uf', 'N/A')}")
        lines.append(f"• CEP: {data.get('cep', 'N/A')}")
        
        return "\n".join(lines)
    
    def process_user_input(self, phone: str, message: str) -> Tuple[ConversationState, str]:
        """
        Processa a entrada do usuário e retorna o próximo estado e mensagem
        
        Returns:
            Tuple[ConversationState, str]: (próximo_estado, mensagem_resposta)
        """
        current_state = self.get_conversation_state(phone)
        message_lower = message.lower().strip()
        
        # Verificar se usuário quer falar com atendente
        if self._is_handoff_request(message_lower):
            self.set_conversation_state(phone, ConversationState.AGUARDANDO_ATENDENTE)
            return ConversationState.AGUARDANDO_ATENDENTE, MessageTemplate.get_template(
                ConversationState.AGUARDANDO_ATENDENTE
            )
        
        # Processar baseado no estado atual
        if current_state == ConversationState.INITIAL:
            return self._process_initial(phone, message_lower)
        
        elif current_state == ConversationState.MENU_PRINCIPAL:
            return self._process_menu_principal(phone, message_lower)
        
        elif current_state == ConversationState.INFO_EMPRESA:
            return self._process_info_empresa(phone, message_lower)
        
        elif current_state == ConversationState.COTACAO_INICIO:
            return self._process_cotacao_inicio(phone, message)
        
        elif current_state == ConversationState.COTACAO_COLETANDO:
            return self._process_cotacao_coletando(phone, message)
        
        elif current_state == ConversationState.COTACAO_VALIDANDO:
            return self._process_cotacao_validando(phone, message_lower)
        
        elif current_state == ConversationState.COTACAO_CONCLUIDA:
            return self._process_cotacao_concluida(phone, message_lower)
        
        elif current_state == ConversationState.POS_COTACAO:
            return self._process_pos_cotacao(phone, message_lower)
        
        else:
            # Estado não reconhecido, resetar
            self.reset_conversation(phone)
            return self._process_initial(phone, message_lower)
    
    def _is_handoff_request(self, message: str) -> bool:
        """Verifica se a mensagem é um pedido para falar com atendente"""
        keywords = [
            'atendente', 'humano', 'pessoa', 'agente', 'operador',
            'falar com alguem', 'falar com alguém', 'falar com uma pessoa',
            'suporte', 'ajuda humana', 'transferir', 'quero falar', 'preciso falar'
        ]
        return any(keyword in message for keyword in keywords)
    
    def _process_initial(self, phone: str, message: str) -> Tuple[ConversationState, str]:
        """Processa estado inicial"""
        self.set_conversation_state(phone, ConversationState.MENU_PRINCIPAL)
        return ConversationState.MENU_PRINCIPAL, MessageTemplate.get_template(
            ConversationState.INITIAL
        )
    
    def _process_menu_principal(self, phone: str, message: str) -> Tuple[ConversationState, str]:
        """Processa menu principal"""
        if message in ['1', 'um', 'empresa', 'saber mais']:
            # Usuário quer saber sobre a empresa
            self.set_conversation_state(phone, ConversationState.INFO_EMPRESA)
            
            # Aqui você pode configurar o texto sobre a empresa
            info_empresa_texto = """Somos especializados em seguros para equinos, oferecendo proteção completa para seu animal.

*Nossos Diferenciais:*
• Cobertura personalizada
• Atendimento especializado
• Processos rápidos e transparentes
• Parceria com as melhores seguradoras

Trabalhamos com seguros para:
• Animais de Competição
• Animais de Exposição
• Rebanhos
• Pecuário Individual"""
            
            return ConversationState.INFO_EMPRESA, MessageTemplate.format_template(
                ConversationState.INFO_EMPRESA,
                info_empresa_texto=info_empresa_texto
            )
        
        elif message in ['2', 'dois', 'cotacao', 'cotação', 'seguro']:
            # Usuário quer fazer cotação
            self.set_conversation_state(phone, ConversationState.COTACAO_INICIO)
            return ConversationState.COTACAO_INICIO, MessageTemplate.get_template(
                ConversationState.COTACAO_INICIO
            )
        
        else:
            # Opção inválida, reenviar menu
            return ConversationState.MENU_PRINCIPAL, MessageTemplate.get_template(
                ConversationState.INITIAL
            ) + "\n\n_Por favor, digite 1 ou 2._"
    
    def _process_info_empresa(self, phone: str, message: str) -> Tuple[ConversationState, str]:
        """Processa informações sobre a empresa"""
        if message in ['1', 'sim', 's']:
            # Usuário quer fazer cotação
            self.set_conversation_state(phone, ConversationState.COTACAO_INICIO)
            return ConversationState.COTACAO_INICIO, MessageTemplate.get_template(
                ConversationState.COTACAO_INICIO
            )
        
        elif message in ['2', 'nao', 'não', 'n']:
            # Usuário não quer cotação
            self.set_conversation_state(phone, ConversationState.ENCERRADA)
            return ConversationState.ENCERRADA, MessageTemplate.get_template(
                ConversationState.ENCERRADA
            )
        
        elif message in ['menu', 'voltar']:
            # Voltar ao menu
            self.set_conversation_state(phone, ConversationState.MENU_PRINCIPAL)
            return ConversationState.MENU_PRINCIPAL, MessageTemplate.get_template(
                ConversationState.INITIAL
            )
        
        else:
            # Resposta inválida
            info_empresa_texto = """Somos especializados em seguros para equinos..."""
            return ConversationState.INFO_EMPRESA, MessageTemplate.format_template(
                ConversationState.INFO_EMPRESA,
                info_empresa_texto=info_empresa_texto
            ) + "\n\n_Por favor, digite 1 para Sim ou 2 para Não._"
    
    def _process_cotacao_inicio(self, phone: str, message: str) -> Tuple[ConversationState, str]:
        """Processa início da cotação - primeira coleta de dados"""
        # Aqui você integraria com seu extrator de dados (OpenAI ou regex)
        # Por enquanto, vamos apenas mudar o estado
        self.set_conversation_state(phone, ConversationState.COTACAO_COLETANDO)
        
        # A mensagem do usuário contém dados, processar com extrator
        # extracted_data = self.extract_data_from_message(message)
        # self.update_conversation_data(phone, extracted_data)
        
        # Retornar template de coleta
        return ConversationState.COTACAO_COLETANDO, MessageTemplate.format_template(
            ConversationState.COTACAO_COLETANDO,
            dados_coletados=self.format_collected_data(phone),
            dados_faltantes=self.format_missing_data(phone)
        )
    
    def _process_cotacao_coletando(self, phone: str, message: str) -> Tuple[ConversationState, str]:
        """Processa coleta de dados da cotação"""
        # Extrair dados da mensagem
        # extracted_data = self.extract_data_from_message(message)
        # self.update_conversation_data(phone, extracted_data)
        
        # Verificar se todos os dados foram coletados
        if self.is_data_complete(phone):
            # Dados completos, ir para validação
            self.set_conversation_state(phone, ConversationState.COTACAO_VALIDANDO)
            return ConversationState.COTACAO_VALIDANDO, MessageTemplate.format_template(
                ConversationState.COTACAO_VALIDANDO,
                resumo_completo=self.format_complete_summary(phone)
            )
        else:
            # Ainda faltam dados
            return ConversationState.COTACAO_COLETANDO, MessageTemplate.format_template(
                ConversationState.COTACAO_COLETANDO,
                dados_coletados=self.format_collected_data(phone),
                dados_faltantes=self.format_missing_data(phone)
            )
    
    def _process_cotacao_validando(self, phone: str, message: str) -> Tuple[ConversationState, str]:
        """Processa validação dos dados coletados"""
        if message in ['1', 'sim', 's', 'correto', 'ok']:
            # Dados confirmados, processar cotação
            self.set_conversation_state(phone, ConversationState.COTACAO_PROCESSANDO)
            return ConversationState.COTACAO_PROCESSANDO, MessageTemplate.get_template(
                ConversationState.COTACAO_PROCESSANDO
            )
        
        elif message in ['2', 'nao', 'não', 'n', 'corrigir']:
            # Usuário quer corrigir, voltar para coleta
            self.set_conversation_state(phone, ConversationState.COTACAO_COLETANDO)
            return ConversationState.COTACAO_COLETANDO, (
                "Ok! Me diga qual informação está incorreta e qual é o valor correto.\n\n" +
                MessageTemplate.format_template(
                    ConversationState.COTACAO_COLETANDO,
                    dados_coletados=self.format_collected_data(phone),
                    dados_faltantes=self.format_missing_data(phone)
                )
            )
        
        else:
            # Resposta inválida
            return ConversationState.COTACAO_VALIDANDO, MessageTemplate.format_template(
                ConversationState.COTACAO_VALIDANDO,
                resumo_completo=self.format_complete_summary(phone)
            ) + "\n\n_Por favor, digite 1 para confirmar ou 2 para corrigir._"
    
    def _process_cotacao_concluida(self, phone: str, message: str) -> Tuple[ConversationState, str]:
        """Processa opções após cotação concluída"""
        if message in ['1', 'nova', 'nova cotacao', 'nova cotação']:
            # Nova cotação - resetar dados mas manter histórico
            data = self.get_conversation_data(phone)
            self.add_cotacao_realizada(phone, data.copy())
            self.reset_conversation(phone)
            self.set_conversation_state(phone, ConversationState.COTACAO_INICIO)
            return ConversationState.COTACAO_INICIO, MessageTemplate.get_template(
                ConversationState.COTACAO_INICIO
            )
        
        elif message in ['2', 'atendente', 'humano']:
            # Falar com atendente
            self.set_conversation_state(phone, ConversationState.AGUARDANDO_ATENDENTE)
            return ConversationState.AGUARDANDO_ATENDENTE, MessageTemplate.get_template(
                ConversationState.AGUARDANDO_ATENDENTE
            )
        
        elif message in ['3', 'encerrar', 'tchau', 'obrigado']:
            # Encerrar
            self.set_conversation_state(phone, ConversationState.ENCERRADA)
            return ConversationState.ENCERRADA, MessageTemplate.get_template(
                ConversationState.ENCERRADA
            )
        
        else:
            # Opção inválida
            return ConversationState.COTACAO_CONCLUIDA, MessageTemplate.format_template(
                ConversationState.COTACAO_CONCLUIDA,
                mensagem_resultado="Cotação enviada com sucesso!"
            ) + "\n\n_Por favor, digite 1, 2 ou 3._"
    
    def _process_pos_cotacao(self, phone: str, message: str) -> Tuple[ConversationState, str]:
        """Processa menu pós-cotação"""
        if message in ['1', 'nova', 'nova cotacao']:
            # Nova cotação
            data = self.get_conversation_data(phone)
            self.add_cotacao_realizada(phone, data.copy())
            self.reset_conversation(phone)
            self.set_conversation_state(phone, ConversationState.COTACAO_INICIO)
            return ConversationState.COTACAO_INICIO, MessageTemplate.get_template(
                ConversationState.COTACAO_INICIO
            )
        
        elif message in ['2', 'empresa', 'informacoes']:
            # Informações sobre empresa
            self.set_conversation_state(phone, ConversationState.INFO_EMPRESA)
            info_empresa_texto = """Somos especializados em seguros para equinos..."""
            return ConversationState.INFO_EMPRESA, MessageTemplate.format_template(
                ConversationState.INFO_EMPRESA,
                info_empresa_texto=info_empresa_texto
            )
        
        elif message in ['3', 'atendente', 'humano']:
            # Atendente
            self.set_conversation_state(phone, ConversationState.AGUARDANDO_ATENDENTE)
            return ConversationState.AGUARDANDO_ATENDENTE, MessageTemplate.get_template(
                ConversationState.AGUARDANDO_ATENDENTE
            )
        
        elif message in ['4', 'encerrar', 'tchau']:
            # Encerrar
            self.set_conversation_state(phone, ConversationState.ENCERRADA)
            return ConversationState.ENCERRADA, MessageTemplate.get_template(
                ConversationState.ENCERRADA
            )
        
        else:
            # Opção inválida
            return ConversationState.POS_COTACAO, MessageTemplate.get_template(
                ConversationState.POS_COTACAO
            ) + "\n\n_Por favor, digite um número de 1 a 4._"


# Instância global do gerenciador de fluxo
conversation_flow = ConversationFlow()
