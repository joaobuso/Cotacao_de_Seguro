# -*- coding: utf-8 -*-
"""
Sistema Centralizado de Fluxo de Conversação - NOVA VERSÃO
Gerencia estados, transições e templates de mensagens
Baseado no novo roteiro de atendimento Equinos Seguros
"""
import os
import json
import logging
from enum import Enum
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta

from app.bot.data_extractor import data_extractor
from app.bot.faq_knowledge import FAQ_TOPICS, find_topic_by_message

logger = logging.getLogger(__name__)


class ConversationState(Enum):
    """Estados possíveis da conversa"""
    INITIAL = "initial"
    MENU_PRINCIPAL = "menu_principal"
    FAQ_RESPOSTA = "faq_resposta"
    COTACAO_INICIO = "cotacao_inicio"
    COTACAO_COLETANDO = "cotacao_coletando"
    COTACAO_VALIDANDO = "cotacao_validando"
    COTACAO_PROCESSANDO = "cotacao_processando"
    COTACAO_CONCLUIDA = "cotacao_concluida"
    POS_COTACAO = "pos_cotacao"
    AGUARDANDO_ATENDENTE = "aguardando_atendente"
    ATENDENTE_ATIVO = "atendente_ativo"
    ENCERRADA = "encerrada"
    COTACAO_EDITANDO = "cotacao_editando"


class MessageTemplate:
    """Templates de mensagens organizados por estado"""

    TEMPLATES = {
        ConversationState.INITIAL: """*Olá! Bem-vindo à Equinos Seguros!* 🐴

Sou seu assistente virtual e estou aqui para ajudá-lo.

*Como posso te ajudar hoje?*

Digite o número da opção desejada:

*1* - Cotação de seguro para cavalo
*2* - Como funciona o seguro para equinos
*3* - Qual valor do seguro

_Você também pode digitar *atendente* a qualquer momento para falar com uma pessoa._""",

        ConversationState.FAQ_RESPOSTA: """{faq_texto}

---
*Posso ajudar com mais alguma coisa?*

*1* - Iniciar cotação de seguro
*0* - Voltar ao menu principal

_Ou digite sua dúvida que tentarei responder._""",

        ConversationState.COTACAO_INICIO: """*Ótimo! Vamos iniciar sua cotação de seguro.* 🐴

Para gerar uma cotação personalizada, preciso de algumas informações:

*DADOS NECESSÁRIOS:*

*Dados do Solicitante:*
• Nome Completo

*Dados do Animal:*
• Nome do Animal
• Valor do Animal (R$)
• Raça
• Data de Nascimento (DD/MM/AAAA)
• Sexo (inteiro, castrado ou fêmea)
• Utilização (lazer, salto, laço, etc.)

*Endereço da Cocheira:*
• UF (Estado)

_Pode enviar todos os dados de uma vez ou aos poucos, como preferir!_""",

        ConversationState.COTACAO_COLETANDO: """*Obrigado pelas informações!*

*DADOS JÁ COLETADOS:*
{dados_coletados}

*AINDA PRECISO DE:*
{dados_faltantes}

Por favor, envie as informações que ainda faltam.

_Digite *atendente* se precisar de ajuda humana._""",

        ConversationState.COTACAO_VALIDANDO: """*Perfeito! Coletei todas as informações necessárias.*

*RESUMO DOS DADOS:*
{resumo_completo}

*Está tudo correto?*

Digite:
*1* - Sim, processar cotação
*2* - Não, preciso corrigir algo

_Se precisar corrigir, basta me dizer qual informação está errada._""",

        ConversationState.COTACAO_PROCESSANDO: """*Processando sua cotação...*

Estou enviando seus dados para o sistema da seguradora e gerando sua proposta personalizada.

*Isso pode levar alguns minutos.*

Assim que a cotação estiver pronta, enviarei o documento PDF com todos os detalhes.

_Por favor, aguarde..._""",

        ConversationState.COTACAO_CONCLUIDA: """*Cotação realizada com sucesso!*

Sua proposta de seguro foi gerada e está sendo enviada agora.

{mensagem_resultado}

*Deseja mais alguma informação?*

Digite:
*1* - Fazer nova cotação
*2* - Falar com atendente
*3* - Encerrar atendimento""",

        ConversationState.POS_COTACAO: """*Como posso ajudar mais?*

Digite o número da opção desejada:

*1* - Fazer nova cotação
*2* - Tirar dúvidas sobre o seguro
*3* - Falar com atendente humano
*4* - Encerrar atendimento""",

        ConversationState.AGUARDANDO_ATENDENTE: """*Transferindo para atendente humano...*

Entendi que você gostaria de falar com um de nossos especialistas.

Um atendente irá assumir esta conversa em breve.

*Por favor, aguarde um momento.*

_Suas mensagens estão sendo registradas e o atendente verá todo o histórico da conversa._""",

        ConversationState.ATENDENTE_ATIVO: """*Atendente humano conectado*

Um de nossos especialistas assumiu esta conversa e irá responder suas mensagens.

_Continue enviando suas dúvidas que o atendente irá ajudá-lo._""",

        ConversationState.ENCERRADA: """*Obrigado por usar a Equinos Seguros!* 🐴

Foi um prazer atendê-lo.

Se precisar de qualquer coisa, é só enviar uma mensagem que estarei aqui para ajudar!

*Até logo!*"""
    }

    @staticmethod
    def get_template(state: ConversationState) -> str:
        return MessageTemplate.TEMPLATES.get(state, "")

    @staticmethod
    def format_template(state: ConversationState, **kwargs) -> str:
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

    # Campos obrigatórios para cotação (SEM e-mail conforme novo roteiro)
    REQUIRED_FIELDS = {
        'nome_solicitante': 'Nome do Solicitante',
        'nome_animal': 'Nome do Animal',
        'valor_animal': 'Valor do Animal',
        'raca': 'Raça',
        'data_nascimento': 'Data de Nascimento',
        'sexo': 'Sexo',
        'utilizacao': 'Utilização',
        'uf': 'UF'
    }

    CONVERSATION_TIMEOUT = timedelta(minutes=10)
    AGENT_TIMEOUT = timedelta(hours=24)

    def __init__(self, ultramsg_api=None):
        self.conversations = {}
        self.ultramsg_api = ultramsg_api

    def get_conversation_state(self, phone: str) -> ConversationState:
        if phone not in self.conversations:
            return ConversationState.INITIAL

        conv = self.conversations[phone]
        last_interaction = conv.get('last_interaction')

        logger.info(f"[STATE] phones em memória: {list(self.conversations.keys())}")
        logger.info(f"[STATE] phone atual: {phone}")

        if last_interaction:
            time_diff = datetime.now() - last_interaction

            # 🔥 TIMEOUT GERAL (10 min)
            if time_diff > self.CONVERSATION_TIMEOUT:
                logger.info(f"Timeout de conversa ({phone}) - resetando")
                if conv['state'] not in [
                    ConversationState.COTACAO_COLETANDO,
                    ConversationState.COTACAO_VALIDANDO,
                    ConversationState.MENU_PRINCIPAL,
                    ConversationState.FAQ_RESPOSTA
                ]:
                    self.reset_conversation(phone)
                    return ConversationState.INITIAL

            # Timeout de atendente (mantém)
            if conv['state'] == ConversationState.ATENDENTE_ATIVO:
                if time_diff > self.AGENT_TIMEOUT:
                    self.reset_conversation(phone)
                    return ConversationState.INITIAL

        return conv['state']

    def set_conversation_state(self, phone: str, state: ConversationState):
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
        if phone not in self.conversations:
            self.conversations[phone] = {
                'state': ConversationState.INITIAL,
                'data': {},
                'created_at': datetime.now(),
                'last_interaction': datetime.now(),
                'message_count': 0,
                'cotacoes_realizadas': []
            }

        for k, v in data.items():
            if v and str(v).strip() and str(v).lower() != "none":
                self.conversations[phone]['data'][k] = v

        self.conversations[phone]['last_interaction'] = datetime.now()
        self.conversations[phone]['message_count'] += 1

    def get_conversation_data(self, phone: str) -> Dict:
        if phone not in self.conversations:
            return {}
        return self.conversations[phone]['data']

    def reset_conversation(self, phone: str):
        if phone in self.conversations:
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
        if phone not in self.conversations:
            return
        if 'cotacoes_realizadas' not in self.conversations[phone]:
            self.conversations[phone]['cotacoes_realizadas'] = []
        cotacao_data['timestamp'] = datetime.now().isoformat()
        self.conversations[phone]['cotacoes_realizadas'].append(cotacao_data)

    def get_missing_fields(self, phone: str) -> List[str]:
        data = self.get_conversation_data(phone)
        missing = []
        for field_key, field_name in self.REQUIRED_FIELDS.items():
            if field_key not in data or not data[field_key]:
                missing.append(field_name)
        return missing

    def is_data_complete(self, phone: str) -> bool:
        return len(self.get_missing_fields(phone)) == 0

    def format_collected_data(self, phone: str) -> str:
        data = self.get_conversation_data(phone)
        lines = []
        for field_key, field_name in self.REQUIRED_FIELDS.items():
            if field_key in data and data[field_key]:
                lines.append(f"✅ {field_name}: {data[field_key]}")
        return "\n".join(lines) if lines else "Nenhum dado coletado ainda."

    def format_missing_data(self, phone: str) -> str:
        missing = self.get_missing_fields(phone)
        if not missing:
            return "Todos os dados foram coletados! ✅"
        return "\n".join([f"❌ {field}" for field in missing])

    def format_complete_summary(self, phone: str) -> str:
        data = self.get_conversation_data(phone)
        lines = []

        lines.append("*Dados do Solicitante:*")
        lines.append(f"• Nome: {data.get('nome_solicitante', 'N/A')}")
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
        lines.append(f"• UF: {data.get('uf', 'N/A')}")

        return "\n".join(lines)

    # =========================================================================
    # PROCESSAMENTO PRINCIPAL
    # =========================================================================

    def process_user_input(self, phone, message, extracted_data=None):
        """
        Processa a entrada do usuário e retorna o próximo estado e mensagem
        """

        # Sempre atualizar interação
        if phone in self.conversations:
            self.conversations[phone]['last_interaction'] = datetime.now()

        current_state = self.get_conversation_state(phone)
        message_lower = message.lower().strip()

        # 🔥 Se está validando, comandos 1 e 2 têm prioridade
        if current_state == ConversationState.COTACAO_VALIDANDO:
            return self._process_cotacao_validando(phone, message_lower)

        # ---------------------------------------------------------
        # 1. Se está em edição, não chama FAQ e não atualiza dados aqui
        # ---------------------------------------------------------
        if current_state == ConversationState.COTACAO_EDITANDO:
            return self._process_cotacao_editando(phone, message)

        # ---------------------------------------------------------
        # 2. Se recebeu dados de cotação, salva e força fluxo de cotação
        # ---------------------------------------------------------
        if extracted_data:
            campos_cotacao = set(self.REQUIRED_FIELDS.keys())

            tem_dado_cotacao = any(
                k in campos_cotacao and extracted_data.get(k)
                for k in extracted_data.keys()
            )

            if tem_dado_cotacao:
                self.update_conversation_data(phone, extracted_data)

                if current_state in [
                    ConversationState.INITIAL,
                    ConversationState.MENU_PRINCIPAL,
                    ConversationState.COTACAO_INICIO,
                    ConversationState.COTACAO_COLETANDO,
                    ConversationState.COTACAO_VALIDANDO
                ]:
                    if self.is_data_complete(phone):
                        self.set_conversation_state(phone, ConversationState.COTACAO_VALIDANDO)
                        return ConversationState.COTACAO_VALIDANDO, MessageTemplate.format_template(
                            ConversationState.COTACAO_VALIDANDO,
                            resumo_completo=self.format_complete_summary(phone)
                        )

                    self.set_conversation_state(phone, ConversationState.COTACAO_COLETANDO)
                    return ConversationState.COTACAO_COLETANDO, MessageTemplate.format_template(
                        ConversationState.COTACAO_COLETANDO,
                        dados_coletados=self.format_collected_data(phone),
                        dados_faltantes=self.format_missing_data(phone)
                    )

        # ---------------------------------------------------------
        # 3. FAQ por palavra-chave
        # Pode rodar em vários estados da conversa, desde que não esteja
        # em edição, validação final, processamento ou atendimento humano.
        # ---------------------------------------------------------
        current_state = self.get_conversation_state(phone)

        estados_permitidos_faq = [
            ConversationState.INITIAL,
            ConversationState.MENU_PRINCIPAL,
            ConversationState.FAQ_RESPOSTA,
            ConversationState.COTACAO_INICIO,
            ConversationState.COTACAO_COLETANDO,
            ConversationState.COTACAO_CONCLUIDA,
            ConversationState.POS_COTACAO,
        ]

        if current_state in estados_permitidos_faq:
            faq = find_topic_by_message(message)

            if faq:
                faq_texto = f"*{faq['titulo']}*\n\n{faq['resumo']}"

                self.set_conversation_state(phone, ConversationState.FAQ_RESPOSTA)

                return ConversationState.FAQ_RESPOSTA, MessageTemplate.format_template(
                    ConversationState.FAQ_RESPOSTA,
                    faq_texto=faq_texto
                )

        # Verificar se usuário quer falar com atendente
        if self._is_handoff_request(message_lower):
            self.set_conversation_state(phone, ConversationState.AGUARDANDO_ATENDENTE)
            return ConversationState.AGUARDANDO_ATENDENTE, MessageTemplate.get_template(
                ConversationState.AGUARDANDO_ATENDENTE
            )

        # Verificar se quer voltar ao menu
        if message_lower in ['menu', 'voltar', '0'] and current_state not in [
            ConversationState.INITIAL,
            ConversationState.COTACAO_COLETANDO,
            ConversationState.COTACAO_VALIDANDO,
            ConversationState.COTACAO_PROCESSANDO
        ]:
            self.set_conversation_state(phone, ConversationState.MENU_PRINCIPAL)
            return ConversationState.MENU_PRINCIPAL, MessageTemplate.get_template(
                ConversationState.INITIAL
            )

        # Processar baseado no estado atual
        if current_state == ConversationState.INITIAL:
            return self._process_initial(phone, message_lower)

        elif current_state == ConversationState.MENU_PRINCIPAL:
            return self._process_menu_principal(phone, message_lower, message)

        elif current_state == ConversationState.FAQ_RESPOSTA:
            return self._process_faq_resposta(phone, message_lower, message)

        elif current_state == ConversationState.COTACAO_INICIO:
            return self._process_cotacao_inicio(phone, message)

        elif current_state == ConversationState.COTACAO_COLETANDO:
            return self._process_cotacao_coletando(phone, message)

        elif current_state == ConversationState.COTACAO_VALIDANDO:
            return self._process_cotacao_validando(phone, message_lower)

        elif current_state == ConversationState.COTACAO_CONCLUIDA:
            return self._process_cotacao_concluida(phone, message_lower)

        elif current_state == ConversationState.POS_COTACAO:
            return self._process_pos_cotacao(phone, message_lower, message)

        elif current_state == ConversationState.COTACAO_EDITANDO:
            return self._process_cotacao_editando(phone, message)

        else:
            self.reset_conversation(phone)
            return self._process_initial(phone, message_lower)

    def _is_handoff_request(self, message: str) -> bool:
        keywords = [
            'atendente', 'humano', 'pessoa', 'agente', 'operador',
            'falar com alguem', 'falar com alguém', 'falar com uma pessoa',
            'suporte', 'ajuda humana', 'transferir', 'quero falar', 'preciso falar'
        ]
        return any(keyword in message for keyword in keywords)

    def _process_initial(self, phone: str, message: str) -> Tuple[ConversationState, str]:
        self.set_conversation_state(phone, ConversationState.MENU_PRINCIPAL)
        return ConversationState.MENU_PRINCIPAL, MessageTemplate.get_template(
            ConversationState.INITIAL
        )

    def _process_cotacao_editando(self, phone, message):
        conv = self.conversations.get(phone, {})
        campo_edicao = conv.get("campo_edicao")

        mapa_nomes = {
            "nome_solicitante": "Nome do Solicitante",
            "nome_animal": "Nome do Animal",
            "valor_animal": "Valor do Animal",
            "raca": "Raça",
            "data_nascimento": "Data de Nascimento",
            "sexo": "Sexo",
            "utilizacao": "Utilização",
            "uf": "UF"
        }

        # FASE 2: já escolheu o campo, agora grava o novo valor
        if campo_edicao:
            self.conversations[phone]['data'][campo_edicao] = message.strip()
            self.conversations[phone].pop("campo_edicao", None)

            self.set_conversation_state(phone, ConversationState.COTACAO_VALIDANDO)

            return ConversationState.COTACAO_VALIDANDO, (
                f"✅ {mapa_nomes.get(campo_edicao, campo_edicao)} atualizado com sucesso!\n\n" +
                MessageTemplate.format_template(
                    ConversationState.COTACAO_VALIDANDO,
                    resumo_completo=self.format_complete_summary(phone)
                )
            )

        # FASE 1: escolher qual campo editar
        campo = message.lower().strip()

        mapa = {
            "1": "nome_solicitante",
            "nome solicitante": "nome_solicitante",
            "nome do solicitante": "nome_solicitante",

            "2": "nome_animal",
            "nome animal": "nome_animal",
            "nome do animal": "nome_animal",
            "animal": "nome_animal",

            "3": "valor_animal",
            "valor": "valor_animal",
            "valor animal": "valor_animal",
            "valor do animal": "valor_animal",

            "4": "raca",
            "raca": "raca",
            "raça": "raca",

            "5": "data_nascimento",
            "data": "data_nascimento",
            "data nascimento": "data_nascimento",
            "data de nascimento": "data_nascimento",

            "6": "sexo",
            "sexo": "sexo",

            "7": "utilizacao",
            "utilizacao": "utilizacao",
            "utilização": "utilizacao",

            "8": "uf",
            "uf": "uf",
            "estado": "uf"
        }

        for key, field in mapa.items():
            if key == campo or key in campo:
                self.conversations[phone]['campo_edicao'] = field
                return (
                    ConversationState.COTACAO_EDITANDO,
                    f"Qual o novo valor para *{mapa_nomes.get(field, field)}*?"
                )

        return ConversationState.COTACAO_EDITANDO, (
            "Não entendi qual campo deseja alterar.\n\n"
            "Digite uma das opções:\n"
            "1 - Nome do Solicitante\n"
            "2 - Nome do Animal\n"
            "3 - Valor do Animal\n"
            "4 - Raça\n"
            "5 - Data de Nascimento\n"
            "6 - Sexo\n"
            "7 - Utilização\n"
            "8 - UF"
        )
    def _process_menu_principal(self, phone: str, message_lower: str, message_original: str) -> Tuple[ConversationState, str]:
        """Processa menu principal com 3 opções + FAQ inteligente"""

        # Opção 1 - Cotação
        if message_lower in ['1', 'um', 'cotacao', 'cotação', 'seguro', 'quero cotação',
                             'quero fazer cotação', 'cotação de seguro']:
            self.set_conversation_state(phone, ConversationState.COTACAO_INICIO)
            return ConversationState.COTACAO_INICIO, MessageTemplate.get_template(
                ConversationState.COTACAO_INICIO
            )

        # Opção 2 - Como funciona o seguro
        if message_lower in ['2', 'dois', 'como funciona', 'funciona', 'como funciona o seguro']:
            faq_texto = self._build_faq_response_by_id(4)  # Tema 4: Cotação e Contratação
            self.set_conversation_state(phone, ConversationState.FAQ_RESPOSTA)
            return ConversationState.FAQ_RESPOSTA, MessageTemplate.format_template(
                ConversationState.FAQ_RESPOSTA,
                faq_texto=faq_texto
            )

        # Opção 3 - Qual valor do seguro
        if message_lower in ['3', 'tres', 'três', 'valor', 'preço', 'preco',
                             'quanto custa', 'qual valor', 'valor do seguro']:
            faq_texto = self._build_faq_response_by_id(5)  # Tema 5: Preço e Valor
            self.set_conversation_state(phone, ConversationState.FAQ_RESPOSTA)
            return ConversationState.FAQ_RESPOSTA, MessageTemplate.format_template(
                ConversationState.FAQ_RESPOSTA,
                faq_texto=faq_texto
            )

        # Tentar encontrar FAQ por palavras-chave
        topic = find_topic_by_message(message_original)
        if topic:
            faq_texto = f"*{topic['titulo']}*\n\n{topic['resumo']}"
            self.set_conversation_state(phone, ConversationState.FAQ_RESPOSTA)
            return ConversationState.FAQ_RESPOSTA, MessageTemplate.format_template(
                ConversationState.FAQ_RESPOSTA,
                faq_texto=faq_texto
            )

        # Nenhuma opção reconhecida
        return ConversationState.MENU_PRINCIPAL, (
            MessageTemplate.get_template(ConversationState.INITIAL) +
            "\n\n_Por favor, digite 1, 2 ou 3, ou escreva sua dúvida._"
        )

    def _process_faq_resposta(self, phone: str, message_lower: str, message_original: str) -> Tuple[ConversationState, str]:
        """Processa resposta após FAQ"""

        # Opção 1 - Iniciar cotação
        if message_lower in ['1', 'um', 'cotacao', 'cotação', 'sim']:
            self.set_conversation_state(phone, ConversationState.COTACAO_INICIO)
            return ConversationState.COTACAO_INICIO, MessageTemplate.get_template(
                ConversationState.COTACAO_INICIO
            )

        # Opção 0 - Voltar ao menu
        if message_lower in ['0', 'zero', 'menu', 'voltar']:
            self.set_conversation_state(phone, ConversationState.MENU_PRINCIPAL)
            return ConversationState.MENU_PRINCIPAL, MessageTemplate.get_template(
                ConversationState.INITIAL
            )

        # Tentar encontrar outra FAQ
        topic = find_topic_by_message(message_original)
        if topic:
            faq_texto = f"*{topic['titulo']}*\n\n{topic['resumo']}"
            self.set_conversation_state(phone, ConversationState.FAQ_RESPOSTA)
            return ConversationState.FAQ_RESPOSTA, MessageTemplate.format_template(
                ConversationState.FAQ_RESPOSTA,
                faq_texto=faq_texto
            )

        # Não entendeu, oferecer opções
        return ConversationState.FAQ_RESPOSTA, MessageTemplate.format_template(
            ConversationState.FAQ_RESPOSTA,
            faq_texto="Não encontrei uma resposta específica para sua pergunta."
        )

    def _process_cotacao_inicio(self, phone: str, message: str):
        """Processa início da cotação - extrai dados da primeira mensagem"""

        if self.is_data_complete(phone):
            self.set_conversation_state(phone, ConversationState.COTACAO_VALIDANDO)
            return ConversationState.COTACAO_VALIDANDO, MessageTemplate.format_template(
                ConversationState.COTACAO_VALIDANDO,
                resumo_completo=self.format_complete_summary(phone)
            )

        self.set_conversation_state(phone, ConversationState.COTACAO_COLETANDO)
        return ConversationState.COTACAO_COLETANDO, MessageTemplate.format_template(
            ConversationState.COTACAO_COLETANDO,
            dados_coletados=self.format_collected_data(phone),
            dados_faltantes=self.format_missing_data(phone)
        )

    def _process_cotacao_coletando(self, phone: str, message: str):
        """Processa coleta de dados - extrai dados incrementalmente"""

        if self.is_data_complete(phone):
            self.set_conversation_state(phone, ConversationState.COTACAO_VALIDANDO)
            return ConversationState.COTACAO_VALIDANDO, MessageTemplate.format_template(
                ConversationState.COTACAO_VALIDANDO,
                resumo_completo=self.format_complete_summary(phone)
            )

        return ConversationState.COTACAO_COLETANDO, MessageTemplate.format_template(
            ConversationState.COTACAO_COLETANDO,
            dados_coletados=self.format_collected_data(phone),
            dados_faltantes=self.format_missing_data(phone)
        )

    def _process_cotacao_validando(self, phone: str, message: str) -> Tuple[ConversationState, str]:
        """Processa validação dos dados coletados"""
        if message in ['1', 'sim', 's', 'correto', 'ok']:
            self.set_conversation_state(phone, ConversationState.COTACAO_PROCESSANDO)
            return ConversationState.COTACAO_PROCESSANDO, MessageTemplate.get_template(
                ConversationState.COTACAO_PROCESSANDO
            )

        elif message in ['2', 'nao', 'não', 'n', 'corrigir']:
            self.set_conversation_state(phone, ConversationState.COTACAO_EDITANDO)

            return ConversationState.COTACAO_EDITANDO, (
                "Qual informação você deseja corrigir?\n\n"
                "Digite uma das opções:\n"
                "1 - Nome do Solicitante\n"
                "2 - Nome do Animal\n"
                "3 - Valor do Animal\n"
                "4 - Raça\n"
                "5 - Data de Nascimento\n"
                "6 - Sexo\n"
                "7 - Utilização\n"
                "8 - UF"
            )

        else:
            return ConversationState.COTACAO_VALIDANDO, MessageTemplate.format_template(
                ConversationState.COTACAO_VALIDANDO,
                resumo_completo=self.format_complete_summary(phone)
            ) + "\n\n_Por favor, digite 1 para confirmar ou 2 para corrigir._"

    def _process_cotacao_concluida(self, phone: str, message: str) -> Tuple[ConversationState, str]:
        """Processa opções após cotação concluída"""
        if message in ['1', 'nova', 'nova cotacao', 'nova cotação']:
            data = self.get_conversation_data(phone)
            self.add_cotacao_realizada(phone, data.copy())
            self.reset_conversation(phone)
            self.set_conversation_state(phone, ConversationState.COTACAO_INICIO)
            return ConversationState.COTACAO_INICIO, MessageTemplate.get_template(
                ConversationState.COTACAO_INICIO
            )

        elif message in ['2', 'atendente', 'humano']:
            self.set_conversation_state(phone, ConversationState.AGUARDANDO_ATENDENTE)
            return ConversationState.AGUARDANDO_ATENDENTE, MessageTemplate.get_template(
                ConversationState.AGUARDANDO_ATENDENTE
            )

        elif message in ['3', 'encerrar', 'tchau', 'obrigado']:
            self.set_conversation_state(phone, ConversationState.ENCERRADA)
            return ConversationState.ENCERRADA, MessageTemplate.get_template(
                ConversationState.ENCERRADA
            )

        else:
            return ConversationState.COTACAO_CONCLUIDA, MessageTemplate.format_template(
                ConversationState.COTACAO_CONCLUIDA,
                mensagem_resultado="Cotação enviada com sucesso!"
            ) + "\n\n_Por favor, digite 1, 2 ou 3._"

    def _process_pos_cotacao(self, phone: str, message_lower: str, message_original: str) -> Tuple[ConversationState, str]:
        """Processa menu pós-cotação"""
        if message_lower in ['1', 'nova', 'nova cotacao']:
            data = self.get_conversation_data(phone)
            self.add_cotacao_realizada(phone, data.copy())
            self.reset_conversation(phone)
            self.set_conversation_state(phone, ConversationState.COTACAO_INICIO)
            return ConversationState.COTACAO_INICIO, MessageTemplate.get_template(
                ConversationState.COTACAO_INICIO
            )

        elif message_lower in ['2', 'duvida', 'dúvida', 'duvidas', 'dúvidas']:
            self.set_conversation_state(phone, ConversationState.MENU_PRINCIPAL)
            return ConversationState.MENU_PRINCIPAL, MessageTemplate.get_template(
                ConversationState.INITIAL
            )

        elif message_lower in ['3', 'atendente', 'humano']:
            self.set_conversation_state(phone, ConversationState.AGUARDANDO_ATENDENTE)
            return ConversationState.AGUARDANDO_ATENDENTE, MessageTemplate.get_template(
                ConversationState.AGUARDANDO_ATENDENTE
            )

        elif message_lower in ['4', 'encerrar', 'tchau']:
            self.set_conversation_state(phone, ConversationState.ENCERRADA)
            return ConversationState.ENCERRADA, MessageTemplate.get_template(
                ConversationState.ENCERRADA
            )

        else:
            return ConversationState.POS_COTACAO, MessageTemplate.get_template(
                ConversationState.POS_COTACAO
            ) + "\n\n_Por favor, digite um número de 1 a 4._"

    # =========================================================================
    # HELPERS
    # =========================================================================

    def _build_faq_response_by_id(self, topic_id: int) -> str:
        """Constrói resposta FAQ por ID do tópico"""
        topic = FAQ_TOPICS.get(topic_id)
        if topic:
            return f"*{topic['titulo']}*\n\n{topic['resumo']}"
        return "Informação não disponível no momento."


# Instância global do gerenciador de fluxo
conversation_flow = ConversationFlow(None)
