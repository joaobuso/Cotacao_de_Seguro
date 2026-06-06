# -*- coding: utf-8 -*-
import unicodedata
import re

"""
Base de Conhecimento FAQ - Equinos Seguros
Atualizada conforme De/Para do cliente no arquivo "PALAVRAS CHAVES + RESUMO (1).docx".

Observação: o tópico 18 (Reembolso de Despesas de Salvamento) foi excluído pelo cliente.
As palavras-chave de salvamento foram mantidas no tópico 16, conforme o documento.
"""

FAQ_TOPICS = {
    1: {
        "titulo": 'Sobre a Equinos Seguros',
        "palavras_chave": [
            'informações sobre a corretora',
            'equinos seguros',
            'equinosseguros',
            'equinos corretora',
            'corretora equinos',
            'empresa equinos seguros',
            'quem é a equinos seguros',
            'sobre a equinos seguros',
            'o que é equinos seguros',
            'falar com equinos seguros',
            'atendimento equinos seguros',
        ],
        "resumo": """A Equinos Seguros é uma corretora especializada em seguro para cavalos, criada em 03/2024.
Unimos experiência em seguros com a realidade do cavalo de esporte, lazer e reprodução, com foco em:
• soluções de seguro sob medida;
• orientação simples e objetiva;
• atendimento humano, direto e transparente."""
    },
    2: {
        "titulo": 'SUSEP / registro / segurança jurídica',
        "palavras_chave": [
            'susep',
            'número da susep',
            'codigo susep',
            'registro susep',
            'registro na susep',
            'seguro registrado na susep',
            'esse seguro é registrado na susep',
            'equinos seguros susep',
            'swiss re susep',
            'fairfax susep',
            'quero o número da susep',
            'consultar na susep',
            'consultar corretor na susep',
            'consultar seguradora na susep',
            'ver na susep',
            'seguro aprovado na susep',
            'seguro de cavalo é regulamentado',
            'fiscalização susep',
            'seguro é regulamentado',
            'é seguro confiável',
            'é seguro de verdade',
            'é seguro mesmo',
            'é confiável esse seguro',
            'é confiável a equinos seguros',
            'é confiável essa corretora',
            'corretora registrada',
            'corretora registrada na susep',
            'corretor registrado na susep',
            'seguro autorizado susep',
        ],
        "resumo": """A Equinos Seguros atua como corretora, intermediando seguros de cavalos junto a seguradoras autorizadas e fiscalizadas pela SUSEP. Os produtos são das seguradoras parceiras, com planos registrados conforme a legislação.
Nosso número SUSEP é 242158878.
Você pode consultar seguradoras e corretores no site da SUSEP pelo nome ou número de registro."""
    },
    3: {
        "titulo": 'Localização / endereço',
        "palavras_chave": [
            'onde fica a equinos seguros',
            'onde fica a equinos',
            'onde vocês ficam',
            'onde vocês estão',
            'onde é a corretora',
            'endereço equinos seguros',
            'endereço da equinos',
            'qual o endereço de vocês',
            'localização equinos seguros',
            'localização da corretora',
            'cidade da equinos seguros',
            'em que cidade vocês estão',
            'em que cidade fica a corretora',
            'onde é o escritório',
            'onde fica o escritório de vocês',
            'sede equinos seguros',
            'matriz equinos seguros',
            'escritório equinos seguros',
            'contato presencial equinos',
            'atendimento presencial equinos',
            'quero ir até a corretora',
            'quero visitar a corretora',
        ],
        "resumo": """A Equinos Seguros tem sede em São Paulo/SP, mas o atendimento é 100% digital para todo o Brasil (WhatsApp, telefone e e-mail). Também atendemos presencialmente com agendamento:
Av. Moaci, 1220 – Planalto Paulista – São Paulo/SP – CEP 04083-902."""
    },
    4: {
        "titulo": 'Cotação e contratação',
        "palavras_chave": [
            'fazer seguro de cavalo',
            'fazer seguro agora',
            'quero fazer seguro',
            'quero segurar meu cavalo',
            'cotação seguro cavalo',
            'orçamento seguro cavalo',
            'simular seguro',
            'simulação seguro cavalo',
            'contratar seguro cavalo',
            'como contratar o seguro',
            'documentos para contratar',
            'o que precisa para fazer seguro',
        ],
        "resumo": """O seguro protege o valor do seu cavalo em caso de morte por riscos cobertos, como doença, cólica, acidente, raio, incêndio e problemas no transporte, conforme a apólice.

A base é a cobertura de vida (com transporte). Você pode incluir reembolso de despesas veterinárias de emergência (internação, cirurgia, cólica grave) e outras coberturas opcionais, como função esportiva, função reprodutiva, prenhez/potro e roubo/furto qualificado.

Os detalhes (o que cobre, limites e regras) mudam conforme a seguradora e o perfil do cavalo, por isso trabalhamos sempre com cotação personalizada."""
    },
    5: {
        "titulo": 'Preço, valor e pagamento',
        "palavras_chave": [
            'valor'
            'preço do seguro',
            'quanto fica o seguro',
            'quanto custa o seguro',
            'valor seguro cavalo',
            'seguro é caro',
            'seguro barato',
            'quanto vou pagar',
            'forma de pagamento',
            'parcelar seguro',
            'pode parcelar',
            'boleto ou cartão',
            'pagamento no cartão',
            'pagamento no pix',
        ],
        "resumo": """O valor do seguro depende de:
• valor do animal;
• idade, raça e uso;
• coberturas escolhidas.
Em geral, o custo fica em torno de 3% a 7% do valor do cavalo ao ano, com possibilidade de parcelamento, conforme a seguradora. Para saber o valor exato, é preciso fazer a cotação."""
    },
    6: {
        "titulo": 'Vigência do seguro',
        "palavras_chave": [
            'vigência do seguro',
            'vigência seguro cavalo',
            'até quando vale o seguro',
            'data de término do seguro',
            'quando acaba o seguro',
            'quando vence o seguro',
            'validade do seguro',
            'validade da apólice',
            'até que dia meu cavalo está segurado',
            'período de cobertura',
            'período de vigência',
            'seguro está em vigor',
            'seguro ainda está valendo',
            'o seguro ainda cobre meu cavalo',
            'cobertura depois do vencimento',
            'cobre depois que vence',
            'extensão de vigência',
            'prorrogação do seguro',
            'renovar o seguro',
            'renovação do seguro',
            'quando posso renovar',
            'como renovar o seguro',
            'seguro venceu, e agora',
            'seguro de cavalo vencido',
            'seguro vencido ainda cobre',
            'dia que começa a cobertura',
            'a partir de quando começa a cobrir',
            'início de vigência',
            'início da cobertura',
            'data de início do seguro',
        ],
        "resumo": """O seguro normalmente vale por 1 ano, com datas de início e término definidas na apólice (sempre às 24h). Até as 24h do dia final, o cavalo está coberto, desde que o seguro esteja pago em dia. Depois disso, a cobertura se encerra, salvo regras específicas da seguradora."""
    },
    7: {
        "titulo": '',
        "palavras_chave": [
            'comprar cavalo',
            'quero comprar um cavalo',
            'vender cavalo',
            'quero vender meu cavalo',
            'como vender meu cavalo',
            'ajudar a vender cavalo',
            'avaliação de cavalo',
            'avaliar meu cavalo',
            'quanto vale meu cavalo',
            'preço do meu cavalo',
            'quanto custa meu cavalo',
            'laudo para compra de cavalo',
            'análise para comprar cavalo',
            'consultar cavalo antes de comprar',
            'exame para comprar cavalo',
            'vistoria para compra de cavalo',
            'vocês vendem cavalo',
            'vocês compram cavalo',
            'intermediação de cavalo',
            'corretagem de cavalo',
            'ajuda para negociar cavalo',
            'dúvida sobre contrato de compra e venda de cavalo',
        ],
        "resumo": """PARA:
7. Compra e venda de cavalos (não atuamos)
A Equinos Seguros é especializada em SEGURO, não em compra e venda de cavalos.
Não fazemos:
• compra, venda ou intermediação de negócios/leilões;
• avaliação de preço ou laudos de compra e venda.
Nossa função é proteger financeiramente o cavalo (morte, cólica, função esportiva, reprodutiva, prenhez, emergências, roubo/furto qualificado, conforme a seguradora)."""
    },
    8: {
        "titulo": 'Cavalo doente, pré-existência e exames',
        "palavras_chave": [
            'cavalo doente pode fazer seguro',
            'já tem problema de saúde',
            'doença pré existente',
            'pré existência',
            'seguro cobre doença antiga',
            'cavalo manca já',
            'cavalo com lesão antiga',
            'precisa de exame veterinário',
            'precisa de atestado',
            'laudo veterinário para seguro',
            'exame para o seguro',
            'cavalo com dor',
        ],
        "resumo": """O seguro é feito para eventos futuros e imprevisíveis.
Em geral:
• doenças pré-existentes, lesões antigas ou problemas já conhecidos não são cobertos;
• a seguradora pode exigir atestado e exames antes de aceitar o risco.
Ainda assim, muitos cavalos com histórico podem ser segurados, com possíveis restrições/exclusões na apólice. Cada caso é analisado individualmente."""
    },
    9: {
        "titulo": 'Transporte e viagem dentro do Brasil',
        "palavras_chave": [
            'transporte cavalo',
            'viagem cavalo',
            'levar cavalo para outra cidade',
            'cavalo viajando dentro do brasil',
            'prova em outro estado',
            'campeonato em outro estado',
            'morte em transporte',
            'seguro cobre transporte',
            'mudar o cavalo de haras',
            'cavalo em treinamento em outro lugar',
        ],
        "resumo": """Na cobertura básica de vida, o cavalo tem cobertura em viagens dentro do Brasil, inclusive durante transporte terrestre, aéreo, marítimo ou ferroviário, desde que:
• o transporte seja adequado;
• o cavalo esteja dentro do território coberto;
• sejam respeitadas as regras da seguradora.
Mudança permanente de haras/cidade deve ser informada para atualizar o local de risco."""
    },
    10: {
        "titulo": 'Dúvidas veterinárias (não somos clínica)',
        "palavras_chave": [
            'meu cavalo está doente',
            'meu cavalo passou mal',
            'cavalo mancando',
            'cavalo manqueira',
            'cavalo com febre',
            'cavalo com cólica o que fazer',
            'emergência veterinária agora',
            'preciso de veterinário',
            'indicação de veterinário',
            'vocês são veterinários',
            'atendimento veterinário',
            'segunda opinião veterinária',
            'análise de exame do cavalo',
        ],
        "resumo": """A Equinos Seguros é corretora de seguro, não clínica veterinária.
Não fazemos:
• atendimento veterinário;
• diagnóstico ou indicação de tratamento;
• análise técnica de exames.
Em caso de problema de saúde, primeiro fale com um médico veterinário.
Depois do atendimento, avaliamos se o caso pode ser analisado pelo seguro, conforme a apólice."""
    },
    11: {
        "titulo": 'Cobertura básica – Vida do Animal',
        "palavras_chave": [
            'morte do cavalo',
            'seguro de vida cavalo',
            'seguro cavalo',
            'vida e transporte',
            'seguro de cavalo atleta',
            'cobre cólica',
            'cólica cavalo',
            'morte por doença',
            'morte por acidente',
            'morte em transporte',
            'morte em viagem',
            'morte em prova',
            'eutanásia coberta',
            'eutanásia cavalo',
            'morte em incêndio',
            'morte por raio',
            'morte por vendaval',
        ],
        "resumo": """Cobertura principal do seguro: indeniza em caso de morte do cavalo por riscos cobertos, como:
• acidentes;
• doenças (incluindo síndrome cólica);
• asfixia, eletrocussão, vendaval, incêndio, explosão e raio;
• envenenamento/intoxicação acidental, ingestão de corpo estranho;
• ataque/picada/mordedura de outros animais;
• complicações de parto;
• eutanásia indicada por veterinário, nos casos previstos;
• morte durante transporte adequado.
Sempre conforme regras e exclusões da apólice (pré-existência, manejo, vacinas etc.)."""
    },
    12: {
        "titulo": 'Extensão para Território Internacional',
        "palavras_chave": [
            'cobertura internacional',
            'viagem internacional',
            'cavalo viajando',
            'cavalo no exterior',
            'competir fora do brasil',
            'prova no exterior',
            'campeonato fora do brasil',
            'seguro fora do brasil',
            'extensão internacional',
        ],
        "resumo": """Cobertura adicional que estende a vida do animal para sinistros ocorridos fora do Brasil, quando o cavalo viaja para competir, reproduzir ou participar de eventos/treinos no exterior. Em regra, o cavalo pode ficar até 50% da vigência da apólice no exterior, sem caracterizar mudança definitiva de domicílio, conforme a seguradora."""
    },
    13: {
        "titulo": 'Função Reprodutiva – Garanhão',
        "palavras_chave": [
            'função reprodutiva',
            'função reprodutiva garanhão',
            'seguro de garanhão',
            'seguro reprodutivo cavalo',
            'fertilidade cavalo',
            'cavalo ficou infértil',
            'garanhão infértil',
            'não cobre mais égua',
            'problema de monta',
            'incapacidade reprodutiva',
            'perda de função reprodutiva',
        ],
        "resumo": """Cobertura adicional para garanhões, que pode indenizar quando:
• o cavalo se torna total e permanentemente infértil; ou
• fica permanentemente incapaz de montar por problema locomotor/neurológico; ou
• precisa ser castrado (retirada dos dois testículos) por doença testicular grave.
Não cobre redução parcial de fertilidade, problemas temporários, doenças pré-existentes, criptorquidismo ou afastamento por comportamento."""
    },
    14: {
        "titulo": 'Função Esportiva',
        "palavras_chave": [
            'função esportiva',
            'perda de função esportiva',
            'seguro cavalo de esporte',
            'seguro cavalo atleta',
            'cavalo ficou inapto pra prova',
            'cavalo não serve mais pra esporte',
            'cavalo atleta machucado',
            'invalidez esportiva cavalo',
        ],
        "resumo": """Cobertura adicional que pode indenizar quando o cavalo se torna total e permanentemente inapto para a modalidade esportiva declarada na apólice (salto, tambor, laço, corrida etc.), por risco coberto.
Não cobre:
• lesões apenas estéticas;
• doenças genéticas/degenerativas;
• uso em atividade diferente da declarada;
• simples redução de performance."""
    },
    15: {
        "titulo": '• Somente prenhez: cobre a morte do feto durante a gestação, até o parto.\n• Prenhez ao desmame: começa na gestação e segue cobrindo o potro recém-nascido até o desmame, conforme condições da seguradora.',
        "palavras_chave": [
            'prenhez ao desmame',
            'seguro de prenhez',
            'seguro do potro',
            'seguro do embrião',
            'morte de potro',
            'morte de feto',
            'morte de embrião',
            'potro até 4 meses',
            'prenhez cavalo',
        ],
        "resumo": """
Prenhez e Potro ao Desmame
Permite proteger:
• somente prenhez: morte do feto durante a gestação, até o parto;
• prenhez ao desmame: da gestação até o potro completar, em geral, até 4 meses (desmame), conforme a seguradora.
Indeniza o valor do feto/potro em caso de morte por riscos cobertos, dentro do período contratado."""
    },
    16: {
        "titulo": 'Reembolso de Despesas Veterinárias (emergência)',
        "palavras_chave": [
            'emergência veterinária',
            'despesa veterinária',
            'reembolso veterinário',
            'reembolso despesas veterinárias',
            'internação cavalo',
            'UTI cavalo',
            'cirurgia emergência',
            'cólica emergência',
            'pronto atendimento cavalo',
            'atendimento na propriedade',
            'hospital veterinário cavalo',
            'salvamento cavalo',
            'despesas de salvamento',
            'reembolso salvamento',
            'resgate cavalo',
            'custo para salvar o cavalo',
            'evitar morte cavalo',
            'emergência salvamento cavalo',
        ],
        "resumo": """Cobertura de reembolso em casos de emergência com risco de morte, que exigem atendimento urgente e, em geral, internação.
Dentro do limite contratado, podem ser reembolsados (com nota fiscal/recibo):
• transporte até clínica/hospital e retorno;
• honorários do veterinário e equipe;
• diárias de internação;
• exames;
• medicamentos;
• atendimento emergencial na propriedade, quando previsto.
Não cobre rotina, prevenção, estética ou casos sem risco imediato à vida.
Há limite máximo e POS/franquia definidos na apólice.
Em alguns produtos, despesas de salvamento também são tratadas dentro dessa cobertura, conforme as condições do seguro."""
    },
    17: {
        "titulo": 'Reembolso de Necropsia',
        "palavras_chave": [
            'necropsia',
            'reembolso de necropsia',
            'exame causa da morte',
            'custo de necropsia',
            'exame post mortem',
            'laudo de necropsia cavalo',
        ],
        "resumo": """Cobertura adicional que reembolsa despesas com necropsia e exames necessários para determinar a causa da morte do cavalo, feitos por veterinário e laboratório habilitados.
Inclui, dentro do limite contratado:
• transporte do corpo;
• honorários da equipe;
• exames laboratoriais."""
    },
    19: {
        "titulo": 'Reembolso de Despesas Odontológicas',
        "palavras_chave": [
            'dente do cavalo',
            'problema dentário',
            'problema odontológico cavalo',
            'cirurgia odontológica',
            'cirurgia dentária cavalo',
            'fratura de mandíbula',
            'despesa odontológica',
            'tratamento dental cavalo',
            'tratamento odontológico cavalo',
        ],
        "resumo": """Cobertura adicional que reembolsa procedimentos cirúrgicos odontológicos para tratar problemas dentários (afecções dentárias), conforme a apólice.
Podem estar cobertos:
• internação;
• honorários da equipe veterinária/cirúrgica;
• exames (como radiografias);
• medicamentos ligados ao procedimento/internação.
Não cobre:
• problemas dentários pré-existentes;
• manutenção preventiva (retirada de pontas, profilaxia, dente do lobo sem indicação clínica);
• procedimentos estéticos ou experimentais."""
    },
    20: {
        "titulo": 'Roubo e Furto Qualificado',
        "palavras_chave": [
            'roubo',
            'furto',
            'roubo e furto',
            'furto qualificado',
            'roubo qualificado',
            'roubo cavalo',
            'furto cavalo',
            'roubo de cavalo',
            'furto de cavalo',
            'cavalo roubado',
            'cavalo furtado',
            'seguro contra roubo',
            'seguro contra roubo de cavalo',
            'roubo fairfax',
            'furto fairfax',
            'roubo e furto cavalo',
        ],
        "resumo": """Cobertura que protege o cavalo em caso de roubo ou furto qualificado no local de risco informado na apólice (haras/propriedade).
Cobre quando o cavalo é:
• roubado com violência ou grave ameaça; ou
• furtado com vestígios claros (arrombamento, quebra de cadeado, destruição de obstáculos, chave falsa, fraude, abuso de confiança ou concurso de pessoas), comprovados, por exemplo, com boletim de ocorrência.
Não cobre furto simples, desaparecimento sem vestígios, roubo/furto em transporte ou fora do local de risco (sem autorização da seguradora)."""
    },
    21: {
        "titulo": 'Sinistro – o que fazer',
        "palavras_chave": [
            'meu cavalo morreu',
            'o cavalo faleceu',
            'perdi meu cavalo',
            'aconteceu um sinistro',
            'acionar o seguro',
            'acionei o seguro',
            'como acionar o seguro',
            'como funciona o sinistro',
            'comunicação de sinistro',
            'aviso de sinistro',
            'que documentos precisa no sinistro',
            'morreu e agora',
            'cavalo com cólica o que fazer',
            'meu cavalo passou mal',
        ],
        "resumo": """Se o cavalo sofreu acidente grave, cólica forte ou veio a óbito:
• Chame um médico veterinário imediatamente e faça o atendimento de emergência.
• Siga a orientação do veterinário (internação, cirurgia ou eutanásia, quando necessária).
• Avise a corretora/seguradora o mais rápido possível, informando:
• número da apólice;
• o que aconteceu;
• data, hora e local.
• Guarde e envie:
• relatórios e atestados veterinários;
• exames, notas fiscais, laudo de necropsia (quando houver);
• fotos, vídeos e demais comprovantes.
Avisar rápido e tentar salvar/minorar o dano é obrigação do segurado e ajuda muito na análise do sinistro.
Para falar com um atendente, digite “atendente”."""
    },
}


def normalizar_texto(texto: str) -> str:
    """Normaliza texto para comparação sem acento, caixa ou pontuação."""
    texto = (texto or "").lower().strip()

    texto = unicodedata.normalize("NFD", texto)
    texto = "".join(
        char for char in texto
        if unicodedata.category(char) != "Mn"
    )

    texto = re.sub(r"[^a-z0-9\s]", " ", texto)
    texto = re.sub(r"\s+", " ", texto)

    return texto


def get_all_keywords_map():
    """Retorna um dicionário {palavra_chave_normalizada: topic_id} para busca rápida."""
    keyword_map = {}
    for topic_id, topic in FAQ_TOPICS.items():
        for kw in topic["palavras_chave"]:
            keyword_map[normalizar_texto(kw)] = topic_id
    return keyword_map


def find_topic_by_message(message: str) -> dict | None:
    """
    Tenta encontrar um tópico FAQ baseado na mensagem do usuário.
    Retorna o tópico encontrado ou None.
    """

    message_normalized = normalizar_texto(message)

    best_match = None
    best_score = 0

    for topic in FAQ_TOPICS.values():
        score = 0

        for kw in topic["palavras_chave"]:
            kw_normalized = normalizar_texto(kw)

            if kw_normalized and kw_normalized in message_normalized:
                # Quanto maior/específica a palavra-chave, maior a pontuação.
                score += len(kw_normalized.split())

        if score > best_score:
            best_score = score
            best_match = topic

    if best_score >= 1:
        return best_match

    return None
