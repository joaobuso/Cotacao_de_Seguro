import unicodedata
import re

# -*- coding: utf-8 -*-
"""
Base de Conhecimento FAQ - Equinos Seguros
21 temas com palavras-chave e resumos para resposta automática via IA
"""

FAQ_TOPICS = {
    1: {
        "titulo": "Sobre a Equinos Seguros",
        "palavras_chave": [
            "informações sobre a corretora", "equinos seguros", "equinosseguros",
            "equinos corretora", "corretora equinos", "empresa equinos seguros",
            "quem é a equinos seguros", "sobre a equinos seguros",
            "o que é equinos seguros", "falar com equinos seguros",
            "atendimento equinos seguros"
        ],
        "resumo": """A Equinos Seguros nasceu da paixão pelos cavalos.
Criada em 25/03/2024, é uma corretora especializada em seguro para cavalos, unindo experiência em seguros com conhecimento da realidade do cavalo de esporte, lazer e reprodução.

Nosso foco é oferecer:
• soluções de seguro sob medida para equinos;
• orientação técnica clara;
• atendimento humano, direto e transparente.

Mais do que um produto, é uma forma de cuidar de quem tem o cavalo como parte importante da vida."""
    },
    2: {
        "titulo": "SUSEP / Registro / Segurança Jurídica",
        "palavras_chave": [
            "susep", "número da susep", "codigo susep", "registro susep",
            "registro na susep", "seguro registrado na susep",
            "esse seguro é registrado na susep", "equinos seguros susep",
            "swiss re susep", "fairfax susep", "quero o número da susep",
            "consultar na susep", "consultar corretor na susep",
            "consultar seguradora na susep", "ver na susep",
            "seguro aprovado na susep", "seguro de cavalo é regulamentado",
            "fiscalização susep", "seguro é regulamentado",
            "é seguro confiável", "é seguro de verdade", "é seguro mesmo",
            "é confiável esse seguro", "é confiável a equinos seguros",
            "é confiável essa corretora", "corretora registrada",
            "corretora registrada na susep", "corretor registrado na susep",
            "seguro autorizado susep"
        ],
        "resumo": """A Equinos Seguros atua como corretora de seguros, intermediando seguros de cavalos junto a seguradoras autorizadas e fiscalizadas pela SUSEP. Os produtos (condições gerais, registro, reservas técnicas etc.) são de responsabilidade das seguradoras parceiras, que têm seus planos devidamente registrados na SUSEP, conforme a legislação. Você pode consultar seguradoras e corretores diretamente no site da SUSEP, pelo nome ou número de registro. Nosso número de registro SUSEP é 242158878."""
    },
    3: {
        "titulo": "Localização / Endereço",
        "palavras_chave": [
            "onde fica a equinos seguros", "onde fica a equinos",
            "onde vocês ficam", "onde vocês estão", "onde é a corretora",
            "endereço equinos seguros", "endereço da equinos",
            "qual o endereço de vocês", "localização equinos seguros",
            "localização da corretora", "cidade da equinos seguros",
            "em que cidade vocês estão", "em que cidade fica a corretora",
            "onde é o escritório", "onde fica o escritório de vocês",
            "sede equinos seguros", "matriz equinos seguros",
            "escritório equinos seguros", "contato presencial equinos",
            "atendimento presencial equinos", "quero ir até a corretora",
            "quero visitar a corretora"
        ],
        "resumo": """A Equinos Seguros é uma corretora especializada em seguro para cavalos, com sede em São Paulo/SP. O atendimento é 100% digital, para todo o Brasil, via WhatsApp, telefone e e-mail. Assim, mesmo em outra cidade ou estado, você contrata e usa o seguro normalmente, inclusive em caso de sinistro. Também oferecemos atendimento presencial com agendamento.
Endereço: Av. Moaci, 1220 – Planalto Paulista – São Paulo/SP – CEP 04083-003."""
    },
    4: {
        "titulo": "Como funciona o seguro para equinos",
        "palavras_chave": [
            "fazer seguro de cavalo", "fazer seguro agora", "quero fazer seguro",
            "quero segurar meu cavalo", "cotação seguro cavalo",
            "orçamento seguro cavalo", "simular seguro", "simulação seguro cavalo",
            "contratar seguro cavalo", "como contratar o seguro",
            "documentos para contratar", "o que precisa para fazer seguro"
        ],
        "resumo": """
O seguro para cavalos protege tanto o proprietário quanto o próprio animal. Se o cavalo vier a óbito em decorrência de riscos cobertos na apólice, a seguradora pode indenizar o dono, reduzindo o impacto financeiro da perda. Além disso, é possível contratar uma cobertura adicional de reembolso de despesas veterinárias emergenciais, que pode ser acionada quando a vida do animal estiver em risco, sempre de acordo com as regras do contrato.

A proteção começa com uma cobertura básica de vida e transporte, que cobre, por exemplo: doenças (como cólica), acidentes durante o transporte, raio, choque elétrico, incêndio, explosão e outros riscos previstos em apólice. Também é possível contratar outras coberturas adicionais, conforme as regras de cada seguradora.

Os detalhes exatos (o que cobre, o que não cobre, limites, carências e regras) variam conforme a seguradora e a cotação feita para o seu cavalo. Para te explicar corretamente no contexto do SEU animal, o próximo passo é fazer a cotação.

"""
    },
    5: {
        "titulo": "Valor do Seguro",
        "palavras_chave": [
            "preço do seguro", "quanto fica o seguro", "quanto custa o seguro",
            "valor seguro cavalo", "seguro é caro", "seguro barato",
            "quanto vou pagar", "forma de pagamento", "parcelar seguro",
            "pode parcelar", "boleto ou cartão", "pagamento no cartão",
            "pagamento no pix"
        ],
        "resumo": """
O valor do seguro para cavalos varia de acordo com vários fatores, como: região, valor do animal; idade; utilização; tipo de coberturas contratadas.

De forma geral, o custo do seguro costuma ficar na faixa de aproximadamente 3% a 7% do valor do animal por ano.  Mas isso é apenas uma referência. 

Para saber o valor correto do seguro do SEU cavalo, o próximo passo é fazer a cotação.
        
"""
    },
    6: {
        "titulo": "Vigência do Seguro",
        "palavras_chave": [
            "vigência do seguro", "vigência seguro cavalo",
            "até quando vale o seguro", "data de término do seguro",
            "quando acaba o seguro", "quando vence o seguro",
            "validade do seguro", "validade da apólice",
            "período de cobertura", "período de vigência",
            "renovar o seguro", "renovação do seguro",
            "quando posso renovar", "como renovar o seguro",
            "seguro venceu", "início de vigência", "início da cobertura",
            "data de início do seguro"
        ],
        "resumo": """O seguro do cavalo normalmente tem vigência de 1 ano, com datas de início e término definidas na apólice (sempre às 24h da data indicada). Até as 24h do dia de término, o cavalo está coberto, desde que o seguro esteja pago em dia. Após esse horário, a cobertura se encerra, salvo situações específicas previstas pela seguradora."""
    },
    7: {
        "titulo": "Compra e Venda de Cavalos (não atuamos)",
        "palavras_chave": [
            "comprar cavalo", "quero comprar um cavalo", "vender cavalo",
            "quero vender meu cavalo", "como vender meu cavalo",
            "ajudar a vender cavalo", "avaliação de cavalo",
            "avaliar meu cavalo", "quanto vale meu cavalo",
            "preço do meu cavalo", "vocês vendem cavalo",
            "vocês compram cavalo", "intermediação de cavalo",
            "corretagem de cavalo"
        ],
        "resumo": """A Equinos Seguros é uma corretora especializada em SEGURO para cavalos. Nós não trabalhamos com:
• compra ou venda de cavalos;
• intermediação de negócios ou leilões;
• avaliação de preço ou laudos de compra e venda.

Nossa função é proteger financeiramente o seu cavalo por meio do seguro (morte, cólica, função esportiva, reprodutiva, prenhez, emergências, roubo/furto qualificado, conforme a seguradora).

Para negócios de compra e venda, o ideal é:
• contar com um médico veterinário de confiança para exames e laudos;
• buscar orientação especializada para contratos."""
    },
    8: {
        "titulo": "Cavalo Doente, Pré-existência e Exames",
        "palavras_chave": [
            "cavalo doente pode fazer seguro", "já tem problema de saúde",
            "doença pré existente", "pré existência",
            "seguro cobre doença antiga", "cavalo manca já",
            "cavalo com lesão antiga", "precisa de exame veterinário",
            "precisa de atestado", "laudo veterinário para seguro",
            "exame para o seguro", "cavalo com dor"
        ],
        "resumo": """CAVALO DOENTE, DOENÇAS PRÉ-EXISTENTES E EXAMES
O seguro é feito para eventos futuros e imprevisíveis. Por isso:
• doenças pré-existentes, lesões antigas ou problemas já conhecidos normalmente não são cobertos;
• a seguradora pode pedir atestado veterinário e exames antes de aceitar o risco.

Isso não significa que não dá para segurar o cavalo, e sim que:
• a seguradora vai analisar o histórico de saúde;
• podem existir restrições ou exclusões específicas na apólice.

Cada caso é analisado individualmente."""
    },
    9: {
        "titulo": "Transporte e Viagem dentro do Brasil",
        "palavras_chave": [
            "transporte cavalo", "viagem cavalo",
            "levar cavalo para outra cidade", "cavalo viajando dentro do brasil",
            "prova em outro estado", "campeonato em outro estado",
            "morte em transporte", "seguro cobre transporte",
            "mudar o cavalo de haras", "cavalo em treinamento em outro lugar"
        ],
        "resumo": """TRANSPORTE E VIAGEM DO CAVALO DENTRO DO BRASIL
Na cobertura básica de vida, o cavalo tem cobertura em viagens dentro do Brasil, inclusive durante transporte terrestre, aéreo, marítimo ou ferroviário, desde que:
• o transporte seja feito em condições adequadas;
• o cavalo esteja dentro do território de cobertura da apólice;
• sejam respeitadas as regras da seguradora (por exemplo, informar mudança permanente de endereço do animal).

É importante avisar a corretora se o cavalo for mudar de haras ou cidade de forma permanente, para atualizar o local de risco."""
    },
    10: {
        "titulo": "Dúvidas Veterinárias (não somos clínica)",
        "palavras_chave": [
            "meu cavalo está doente", "meu cavalo passou mal",
            "cavalo mancando", "cavalo manqueira", "cavalo com febre",
            "cavalo com cólica o que fazer", "emergência veterinária agora",
            "preciso de veterinário", "indicação de veterinário",
            "vocês são veterinários", "atendimento veterinário",
            "segunda opinião veterinária", "análise de exame do cavalo"
        ],
        "resumo": """A Equinos Seguros é uma corretora especializada em SEGURO para cavalos. Nós não somos clínica veterinária e não fazemos:
• atendimento veterinário;
• diagnóstico ou indicação de tratamento;
• análise técnica de exames clínicos.

Em caso de problema de saúde com o cavalo:
1. Procure imediatamente um médico veterinário de confiança.
2. Depois do atendimento, podemos orientar se o caso pode ser analisado pelo seguro, conforme a apólice.

O seguro não substitui o veterinário, mas pode ajudar a reduzir o impacto financeiro em emergências."""
    },
    11: {
        "titulo": "Cobertura Básica – Vida do Animal",
        "palavras_chave": [
            "morte do cavalo", "seguro de vida cavalo", "seguro cavalo",
            "vida e transporte", "seguro de cavalo atleta", "cobre cólica",
            "cólica cavalo", "morte por doença", "morte por acidente",
            "morte em transporte", "morte em viagem", "morte em prova",
            "eutanásia coberta", "eutanásia cavalo", "morte em incêndio",
            "morte por raio", "morte por vendaval"
        ],
        "resumo": """COBERTURA BÁSICA – VIDA DO ANIMAL
É a cobertura principal do seguro. Garante indenização ao proprietário em caso de morte do cavalo por eventos cobertos, como:
• acidentes;
• doenças (incluindo síndrome cólica);
• asfixia, eletrocussão, vendaval, incêndio, explosão e raio;
• envenenamento ou intoxicação acidental, ingestão acidental de corpo estranho;
• ataque, picada ou mordedura de outros animais;
• complicações de parto;
• eutanásia indicada por médico veterinário, nas situações previstas na apólice;
• morte durante transporte adequado (terrestre, aéreo, marítimo ou ferroviário), por riscos cobertos.

A cobertura segue as regras, limites e exclusões das condições gerais da seguradora."""
    },
    12: {
        "titulo": "Extensão para Território Internacional",
        "palavras_chave": [
            "cobertura internacional", "viagem internacional",
            "cavalo viajando", "cavalo no exterior", "competir fora do brasil",
            "prova no exterior", "campeonato fora do brasil",
            "seguro fora do brasil", "extensão internacional"
        ],
        "resumo": """EXTENSÃO PARA TERRITÓRIO INTERNACIONAL
Cobertura adicional que estende a cobertura de vida para sinistros ocorridos fora do Brasil, por tempo limitado, quando o cavalo viaja para competir, reproduzir ou participar de eventos, incluindo treinamentos no exterior. O cavalo pode permanecer, no máximo, 50% da vigência da apólice em território internacional, sem caracterizar mudança definitiva de domicílio, conforme regras da seguradora."""
    },
    13: {
        "titulo": "Função Reprodutiva – Garanhão",
        "palavras_chave": [
            "função reprodutiva", "função reprodutiva garanhão",
            "seguro de garanhão", "seguro reprodutivo cavalo",
            "fertilidade cavalo", "cavalo ficou infértil",
            "garanhão infértil", "não cobre mais égua",
            "problema de monta", "incapacidade reprodutiva",
            "perda de função reprodutiva"
        ],
        "resumo": """COBERTURA DE FUNÇÃO REPRODUTIVA (GARANHÃO)
Cobertura adicional para garanhões que pode indenizar quando:
• o cavalo se torna total e permanentemente infértil, comprovado por exames seriados; ou
• fica permanentemente incapaz de realizar a monta por problema locomotor ou doença neurológica, sem possibilidade de recuperação completa; ou
• precisa ter os dois testículos retirados (castração) por doença testicular grave.

Não cobre redução parcial de fertilidade, problemas temporários, doenças pré-existentes, criptorquidismo ou afastamento da reprodução por comportamento."""
    },
    14: {
        "titulo": "Função Esportiva",
        "palavras_chave": [
            "função esportiva", "perda de função esportiva",
            "seguro cavalo de esporte", "seguro cavalo atleta",
            "cavalo ficou inapto pra prova", "cavalo não serve mais pra esporte",
            "cavalo atleta machucado", "invalidez esportiva cavalo"
        ],
        "resumo": """COBERTURA DE FUNÇÃO ESPORTIVA
Cobertura adicional que pode indenizar quando o cavalo se torna total e permanentemente inapto para a função esportiva declarada na apólice (salto, tambor, laço, corrida etc.), em decorrência de riscos cobertos.

Não cobre:
• lesões apenas estéticas;
• doenças genéticas ou degenerativas;
• uso em atividade diferente da declarada;
• simples redução de performance, sem incapacidade total e permanente."""
    },
    15: {
        "titulo": "Prenhez e Potro ao Desmame",
        "palavras_chave": [
            "prenhez ao desmame", "seguro de prenhez", "seguro do potro",
            "seguro do embrião", "morte de potro", "morte de feto",
            "morte de embrião", "potro até 4 meses", "prenhez cavalo"
        ],
        "resumo": """COBERTURA DE PRENHEZ E POTRO AO DESMAME
Para quem investe em reprodução, é possível proteger a gestação da égua e, em alguns casos, também o potro nos primeiros meses de vida. Essa cobertura indeniza o valor do feto ou potro em caso de morte por riscos cobertos, dentro do período contratado. Trabalhamos com duas formas principais:
• Somente prenhez: cobre a morte do feto durante a gestação, até o parto.
• Prenhez ao desmame: começa na gestação e segue cobrindo o potro recém-nascido até o desmame, conforme condições da seguradora.

Para contratar e em caso de sinistro, a seguradora pode exigir documentos como: atestado de prenhez, exames (ultrassom), comunicado de cobrição/nascimento na associação da raça, comprovação do valor (nota fiscal, leilão) e laudos veterinários."""
    },
    16: {
        "titulo": "Reembolso de Despesas Veterinárias",
        "palavras_chave": [
            "emergência veterinária", "despesa veterinária",
            "reembolso veterinário", "reembolso despesas veterinárias",
            "internação cavalo", "UTI cavalo", "cirurgia emergência",
            "cólica emergência", "pronto atendimento cavalo",
            "atendimento na propriedade", "hospital veterinário cavalo"
        ],
        "resumo": """COBERTURA DE REEMBOLSO DE DESPESAS VETERINÁRIAS
Essa cobertura não é plano de saúde. Ela serve para reembolsar o segurado em casos de emergência médico-veterinária, com risco de morte do animal, que exijam atendimento e, em geral, internação em clínica ou hospital veterinário, conforme avaliação do veterinário e regras da apólice.

Dentro do limite contratado, podem ser reembolsados, mediante Nota Fiscal/recibo:
• transporte até a clínica/hospital e retorno;
• honorários do médico veterinário e da equipe;
• diárias e custos de internação;
• exames complementares;
• medicamentos usados no atendimento de emergência e na internação.

Não cobre, entre outros:
• casos sem emergência (sem risco imediato à vida);
• consultas de rotina, procedimentos preventivos, estéticos ou eletivos;
• despesas sem comprovação fiscal.

O reembolso é limitado ao valor máximo contratado, já descontada a participação obrigatória do segurado (POS/franquia) prevista na apólice."""
    },
    17: {
        "titulo": "Reembolso de Necropsia",
        "palavras_chave": [
            "necropsia", "reembolso de necropsia", "exame causa da morte",
            "custo de necropsia", "exame post mortem",
            "laudo de necropsia cavalo"
        ],
        "resumo": """REEMBOLSO DE NECROPSIA
Cobertura adicional que reembolsa despesas com necropsia e exames complementares necessários para determinar a causa da morte do cavalo, realizados por médico veterinário e laboratório habilitados.

Podem incluir, conforme a apólice:
• transporte do corpo até o local da necropsia;
• honorários da equipe veterinária;
• exames laboratoriais, toxicológicos, histopatológicos etc.

O reembolso é limitado ao valor contratado para essa cobertura."""
    },
    18: {
        "titulo": "Reembolso de Despesas de Salvamento",
        "palavras_chave": [
            "salvamento cavalo", "despesas de salvamento",
            "reembolso salvamento", "resgate cavalo",
            "custo para salvar o cavalo", "evitar morte cavalo",
            "emergência salvamento cavalo"
        ],
        "resumo": """REEMBOLSO DE DESPESAS DE SALVAMENTO
Cobertura adicional que reembolsa despesas feitas pelo proprietário para tentar evitar um sinistro grave, reduzir danos ou salvar a vida do cavalo em situação de risco imediato, nos casos previstos na apólice.

Pode incluir, por exemplo:
• despesas de salvamento durante ou logo após um evento grave;
• danos materiais causados na tentativa de salvar o animal.

Não cobre custos de situações que não sejam emergência real ou que não representem ameaça direta e imediata à vida do cavalo."""
    },
    19: {
        "titulo": "Reembolso de Despesas Odontológicas",
        "palavras_chave": [
            "dente do cavalo", "problema dentário",
            "problema odontológico cavalo", "cirurgia odontológica",
            "cirurgia dentária cavalo", "fratura de mandíbula",
            "despesa odontológica", "tratamento dental cavalo",
            "tratamento odontológico cavalo"
        ],
        "resumo": """REEMBOLSO DE DESPESAS ODONTOLÓGICAS
Cobertura adicional que reembolsa despesas de procedimento cirúrgico para tratar problemas dentários do cavalo (afecções dentárias), conforme regras da seguradora.

Podem estar cobertos:
• internação (estadia, alimentação etc.);
• honorários da equipe veterinária e cirúrgica;
• exames (radiografias, ultrassom etc.);
• medicamentos usados durante o procedimento e a internação.

Não cobre:
• problemas dentários pré-existentes;
• manutenção preventiva (como retirada de pontas dentárias, profilaxia de rotina);
• procedimentos estéticos ou experimentais."""
    },
    20: {
        "titulo": "Roubo e Furto Qualificado",
        "palavras_chave": [
            "roubo", "furto", "roubo e furto", "furto qualificado",
            "roubo qualificado", "roubo cavalo", "furto cavalo",
            "roubo de cavalo", "furto de cavalo", "cavalo roubado",
            "cavalo furtado", "seguro contra roubo",
            "seguro contra roubo de cavalo", "roubo fairfax",
            "furto fairfax", "roubo e furto cavalo"
        ],
        "resumo": """COBERTURA DE ROUBO E FURTO QUALIFICADO DO CAVALO
Essa cobertura protege o SEU cavalo caso ele seja levado por roubo ou furto qualificado no local onde fica alojado (propriedade/haras informado na apólice).

Ela pode ser acionada quando o cavalo é:
• roubado com violência ou grave ameaça; ou
• furtado com indícios claros de arrombamento, quebra de cadeado, destruição de obstáculos, uso de chave falsa, fraude, abuso de confiança ou participação de mais de uma pessoa; desde que isso seja comprovado (por exemplo, com boletim de ocorrência e demais documentos exigidos).

Ficam de fora, entre outros:
• furto simples ou desaparecimento sem vestígios;
• roubo/furto durante transporte;
• eventos fora do local de risco informado, salvo se houver autorização da seguradora."""
    },
    21: {
        "titulo": "Sinistro – O que Fazer",
        "palavras_chave": [
            "meu cavalo morreu", "o cavalo faleceu", "perdi meu cavalo",
            "aconteceu um sinistro", "acionar o seguro", "acionei o seguro",
            "como acionar o seguro", "como funciona o sinistro",
            "comunicação de sinistro", "aviso de sinistro",
            "que documentos precisa no sinistro", "morreu e agora",
            "cavalo com cólica o que fazer", "meu cavalo passou mal"
        ],
        "resumo": """O QUE FAZER EM CASO DE SINISTRO (PROBLEMA COM O CAVALO)
Se o seu cavalo sofreu um acidente grave, está com cólica forte ou veio a óbito, siga estes passos:

1. Chame um médico veterinário imediatamente e faça o atendimento de emergência.
2. Siga a orientação do veterinário quanto a internação, cirurgia ou eutanásia (quando necessária).
3. Avise a corretora/seguradora o quanto antes, informando:
   • número da apólice;
   • o que aconteceu;
   • data, hora e local.
4. Guarde e envie toda a documentação:
   • relatórios e atestados veterinários;
   • exames, notas fiscais, laudos de necropsia (quando solicitada);
   • fotos, vídeos e demais comprovantes.

Cada seguradora tem regras específicas, mas quanto mais rápido for o aviso, mais fácil é analisar o caso. Para falar com um atendente, digite "atendente"."""
    }
}

def normalizar_texto(texto: str) -> str:
    texto = texto.lower().strip()

    texto = unicodedata.normalize("NFD", texto)
    texto = "".join(
        char for char in texto
        if unicodedata.category(char) != "Mn"
    )

    texto = re.sub(r"[^a-z0-9\s]", " ", texto)
    texto = re.sub(r"\s+", " ", texto)

    return texto

def get_all_keywords_map():
    """Retorna um dicionário {palavra_chave: topic_id} para busca rápida"""
    keyword_map = {}
    for topic_id, topic in FAQ_TOPICS.items():
        for kw in topic["palavras_chave"]:
            keyword_map[kw.lower()] = topic_id
    return keyword_map


def find_topic_by_message(message: str) -> dict:
    """
    Tenta encontrar um tópico FAQ baseado na mensagem do usuário.
    Retorna o tópico encontrado ou None.
    """

    message_normalized = normalizar_texto(message)

    best_match = None
    best_score = 0

    for topic_id, topic in FAQ_TOPICS.items():
        score = 0

        for kw in topic["palavras_chave"]:
            kw_normalized = normalizar_texto(kw)

            if kw_normalized in message_normalized:
                # Quanto maior/específica a palavra-chave, maior a pontuação
                score += len(kw_normalized.split())

        if score > best_score:
            best_score = score
            best_match = topic

    if best_score >= 1:
        return best_match

    return None