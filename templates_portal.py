# Templates HTML para o Portal Completo

DASHBOARD_COMPLETE_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Portal Completo - {{ agent_name }}</title>
    <meta charset="utf-8">
    <style>
        body { font-family: Arial, sans-serif; margin: 0; background: #f5f5f5; }
        .header { background: #007bff; color: white; padding: 15px 20px; display: flex; justify-content: space-between; align-items: center; }
        .container { padding: 20px; }
        .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-bottom: 30px; }
        .stat-card { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); text-align: center; }
        .stat-number { font-size: 32px; font-weight: bold; }
        .stat-label { color: #666; margin-top: 5px; }
        .bot-stat { color: #28a745; }
        .human-stat { color: #dc3545; }
        .quotation-stat { color: #17a2b8; }
        .btn { padding: 10px 20px; background: #007bff; color: white; text-decoration: none; border-radius: 4px; margin: 5px; }
        .btn-danger { background: #dc3545; }
        .btn-success { background: #28a745; }
        .btn-info { background: #17a2b8; }
        .section { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin-bottom: 20px; }
        .urgent { border-left: 4px solid #dc3545; }
        .success { border-left: 4px solid #28a745; }
        .item { border-bottom: 1px solid #eee; padding: 15px 0; }
        .phone { font-weight: bold; color: #007bff; }
        .message { color: #666; margin: 5px 0; }
        .timestamp { font-size: 12px; color: #999; }
        .badge { padding: 2px 8px; border-radius: 12px; font-size: 11px; color: white; }
        .badge-danger { background: #dc3545; }
        .badge-success { background: #28a745; }
        .badge-warning { background: #ffc107; color: #000; }
    </style>
</head>
<body>
    <div class="header">
        <h1>🏢 Portal Completo - {{ agent_name }}</h1>
        <div>
            <a href="/agent/conversations" class="btn">💬 Conversas</a>
            <a href="/agent/quotations" class="btn btn-info">📋 Cotações</a>
            <a href="/agent/logout" class="btn">🚪 Sair</a>
        </div>
    </div>
    
    <div class="container">
        <div class="stats">
            <div class="stat-card">
                <div class="stat-number">{{ stats.total_clients }}</div>
                <div class="stat-label">Clientes Totais</div>
            </div>
            <div class="stat-card">
                <div class="stat-number bot-stat">{{ stats.bot_handled }}</div>
                <div class="stat-label">🤖 Atendido pelo Bot</div>
            </div>
            <div class="stat-card">
                <div class="stat-number human-stat">{{ stats.human_handled }}</div>
                <div class="stat-label">👨‍💼 Atendido por Humano</div>
            </div>
            <div class="stat-card">
                <div class="stat-number quotation-stat">{{ stats.quotations_completed }}</div>
                <div class="stat-label">📋 Cotações Finalizadas</div>
            </div>
        </div>
        
        <div class="stats">
            <div class="stat-card">
                <div class="stat-number bot-stat">{{ stats.quotations_by_bot }}</div>
                <div class="stat-label">🤖 Finalizadas pelo Bot</div>
            </div>
            <div class="stat-card">
                <div class="stat-number human-stat">{{ stats.quotations_by_human }}</div>
                <div class="stat-label">👨‍💼 Finalizadas por Humano</div>
            </div>
            <div class="stat-card">
                <div class="stat-number" style="color: #ffc107;">{{ stats.quotations_failed }}</div>
                <div class="stat-label">⚠️ Cotações com Erro</div>
            </div>
            <div class="stat-card">
                <div class="stat-number" style="color: #6c757d;">{{ stats.today_conversations }}</div>
                <div class="stat-label">📅 Conversas Hoje</div>
            </div>
        </div>
        
        {% if human_needed %}
        <div class="section urgent">
            <h3>🚨 Atendimento Humano Necessário ({{ human_needed|length }})</h3>
            {% for conv in human_needed %}
            <div class="item">
                <div class="phone">📱 {{ conv.phone }} <span class="badge badge-danger">URGENTE</span></div>
                <div class="message">"{{ conv.message[:100] }}..."</div>
                <div class="timestamp">{{ conv.timestamp.strftime('%d/%m/%Y %H:%M') }}</div>
                <div style="margin-top: 10px;">
                    <a href="/agent/conversations/{{ conv.phone }}" class="btn btn-danger">💬 Responder Agora</a>
                </div>
            </div>
            {% endfor %}
        </div>
        {% endif %}
        
        {% if recent_quotations %}
        <div class="section success">
            <h3>📋 Cotações Recentes ({{ recent_quotations|length }})</h3>
            {% for quot in recent_quotations %}
            <div class="item">
                <div class="phone">📱 {{ quot.phone }} 
                    {% if quot.completed_by == 'bot' %}
                        <span class="badge badge-success">BOT</span>
                    {% else %}
                        <span class="badge" style="background: #6f42c1;">HUMANO</span>
                    {% endif %}
                    {% if quot.status == 'completed' %}
                        <span class="badge badge-success">FINALIZADA</span>
                    {% elif quot.status == 'failed' %}
                        <span class="badge badge-warning">ERRO</span>
                    {% else %}
                        <span class="badge" style="background: #17a2b8;">PROCESSANDO</span>
                    {% endif %}
                </div>
                <div class="message">Animal: {{ quot.client_data.get('nome_animal', 'N/A') }} - Valor: R$ {{ quot.client_data.get('valor_animal', 'N/A') }}</div>
                <div class="timestamp">{{ quot.created_at.strftime('%d/%m/%Y %H:%M') }}</div>
            </div>
            {% endfor %}
        </div>
        {% endif %}
        
        <div class="section">
            <h3>📊 Performance Geral</h3>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
                <div>
                    <strong>Taxa de Automação:</strong>
                    {% if stats.bot_handled + stats.human_handled > 0 %}
                        {{ "%.1f"|format((stats.bot_handled / (stats.bot_handled + stats.human_handled)) * 100) }}%
                    {% else %}
                        0%
                    {% endif %}
                </div>
                <div>
                    <strong>Taxa de Finalização:</strong>
                    {% if stats.total_clients > 0 %}
                        {{ "%.1f"|format((stats.quotations_completed / stats.total_clients) * 100) }}%
                    {% else %}
                        0%
                    {% endif %}
                </div>
            </div>
        </div>
    </div>
</body>
</html>
"""

CONVERSATIONS_LIST_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Conversas - {{ agent_name }}</title>
    <meta charset="utf-8">
    <style>
        body { font-family: Arial, sans-serif; margin: 0; background: #f5f5f5; }
        .header { background: #007bff; color: white; padding: 15px 20px; display: flex; justify-content: space-between; align-items: center; }
        .container { padding: 20px; }
        .filters { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin-bottom: 20px; }
        .conversation-card { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin-bottom: 15px; }
        .conversation-phone { font-size: 18px; font-weight: bold; color: #007bff; margin-bottom: 10px; }
        .conversation-stats { display: flex; gap: 20px; margin-bottom: 10px; }
        .btn { padding: 8px 16px; background: #007bff; color: white; text-decoration: none; border-radius: 4px; }
        .btn-back { background: #6c757d; }
        .btn-danger { background: #dc3545; }
        .badge { padding: 2px 8px; border-radius: 12px; font-size: 11px; color: white; margin-left: 10px; }
        .badge-danger { background: #dc3545; }
        .badge-success { background: #28a745; }
        .badge-info { background: #17a2b8; }
    </style>
</head>
<body>
    <div class="header">
        <h1>💬 Todas as Conversas</h1>
        <div>
            <a href="/agent/dashboard" class="btn btn-back">⬅ Dashboard</a>
            <a href="/agent/quotations" class="btn btn-info">📋 Cotações</a>
            <a href="/agent/logout" class="btn">🚪 Sair</a>
        </div>
    </div>
    
    <div class="container">
        <div class="filters">
            <h4>📊 Resumo: {{ conversations|length }} conversas ativas</h4>
        </div>
        
        {% for conv in conversations %}
        <div class="conversation-card">
            <div class="conversation-phone">
                📱 {{ conv._id }}
                {% if conv.needs_human %}
                    <span class="badge badge-danger">PRECISA HUMANO</span>
                {% endif %}
                {% if conv.has_human_response %}
                    <span class="badge badge-success">COM RESPOSTA HUMANA</span>
                {% else %}
                    <span class="badge badge-info">APENAS BOT</span>
                {% endif %}
            </div>
            <div class="conversation-stats">
                <span><strong>Total:</strong> {{ conv.message_count }} mensagens</span>
                <span><strong>Última atividade:</strong> {{ conv.last_timestamp.strftime('%d/%m/%Y %H:%M') }}</span>
            </div>
            <div style="margin-bottom: 15px; color: #666;">
                <strong>Última mensagem:</strong> "{{ conv.last_message[:150] }}..."
            </div>
            <div>
                <a href="/agent/conversations/{{ conv._id }}" class="btn">👀 Ver Conversa Completa</a>
                {% if conv.needs_human %}
                    <a href="/agent/conversations/{{ conv._id }}" class="btn btn-danger">🚨 Responder Urgente</a>
                {% endif %}
            </div>
        </div>
        {% endfor %}
        
        {% if not conversations %}
        <div style="text-align: center; padding: 40px; color: #666;">
            <h3>📭 Nenhuma conversa encontrada</h3>
            <p>Aguardando primeiras mensagens dos clientes.</p>
        </div>
        {% endif %}
    </div>
</body>
</html>
"""

CONVERSATION_PORTAL_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Portal de Resposta - {{ phone }}</title>
    <meta charset="utf-8">
    <style>
        body { font-family: Arial, sans-serif; margin: 0; background: #f5f5f5; }
        .header { background: #007bff; color: white; padding: 15px 20px; display: flex; justify-content: space-between; align-items: center; }
        .container { padding: 20px; display: grid; grid-template-columns: 1fr 350px; gap: 20px; height: calc(100vh - 100px); }
        .conversation-panel { background: white; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); display: flex; flex-direction: column; }
        .conversation-header { padding: 20px; border-bottom: 1px solid #eee; }
        .conversation-messages { flex: 1; padding: 20px; overflow-y: auto; max-height: 400px; }
        .conversation-input { padding: 20px; border-top: 1px solid #eee; }
        .client-panel { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .message { margin-bottom: 15px; padding: 15px; border-radius: 8px; }
        .message-user { background: #e3f2fd; border-left: 4px solid #2196f3; }
        .message-bot { background: #f1f8e9; border-left: 4px solid #4caf50; }
        .message-human { background: #fff3e0; border-left: 4px solid #ff9800; }
        .message-header { font-weight: bold; margin-bottom: 8px; }
        .message-content { margin-bottom: 8px; line-height: 1.4; }
        .message-timestamp { font-size: 12px; color: #666; }
        .btn { padding: 8px 16px; background: #007bff; color: white; text-decoration: none; border-radius: 4px; border: none; cursor: pointer; }
        .btn-success { background: #28a745; }
        .btn-danger { background: #dc3545; }
        .form-group { margin-bottom: 15px; }
        .form-control { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 4px; box-sizing: border-box; }
        .textarea { min-height: 100px; resize: vertical; }
        .field { margin-bottom: 10px; }
        .field-label { font-weight: bold; color: #333; }
        .field-value { color: #666; margin-top: 2px; }
        .alert { padding: 10px; border-radius: 4px; margin-bottom: 15px; }
        .alert-success { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
        .alert-danger { background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
    </style>
</head>
<body>
    <div class="header">
        <h1>💬 Portal de Resposta: {{ phone }}</h1>
        <div>
            <a href="/agent/conversations" class="btn">⬅ Voltar</a>
        </div>
    </div>
    
    <div class="container">
        <div class="conversation-panel">
            <div class="conversation-header">
                <h3>📱 Histórico da Conversa</h3>
                <div id="alerts"></div>
            </div>
            
            <div class="conversation-messages" id="messages">
                {% for conv in conversations %}
                <div class="message {% if conv.message_type == 'human' %}message-human{% elif conv.message_type == 'bot' %}message-bot{% else %}message-user{% endif %}">
                    <div class="message-header">
                        {% if conv.message_type == 'human' %}
                            👨‍💼 {{ conv.agent_email or 'Agente' }}
                        {% elif conv.message_type == 'bot' %}
                            🤖 Bot
                        {% else %}
                            👤 Cliente
                        {% endif %}
                        {% if conv.needs_human %}
                            <span style="background: #dc3545; color: white; padding: 2px 8px; border-radius: 12px; font-size: 11px; margin-left: 10px;">QUER HUMANO</span>
                        {% endif %}
                    </div>
                    <div class="message-content">
                        {% if conv.message_type == 'human' or conv.message_type == 'bot' %}
                            {{ conv.response or conv.message }}
                        {% else %}
                            {{ conv.message }}
                        {% endif %}
                    </div>
                    <div class="message-timestamp">{{ conv.timestamp.strftime('%d/%m/%Y %H:%M:%S') }}</div>
                </div>
                {% endfor %}
            </div>
            
            <div class="conversation-input">
                <form id="messageForm">
                    <div class="form-group">
                        <label><strong>💬 Responder como {{ agent_name }}:</strong></label>
                        <textarea name="message" class="form-control textarea" placeholder="Digite sua resposta aqui..." required></textarea>
                    </div>
                    <div style="display: flex; gap: 10px;">
                        <button type="submit" class="btn btn-success">📤 Enviar Mensagem</button>
                        <button type="button" class="btn btn-danger" onclick="completeQuotation()">✅ Finalizar Cotação</button>
                    </div>
                </form>
            </div>
        </div>
        
        <div class="client-panel">
            <h3>📋 Dados do Cliente</h3>
            {% if client_data and client_data.data %}
            {% for key, value in client_data.data.items() %}
            <div class="field">
                <div class="field-label">{{ key.replace('_', ' ').title() }}:</div>
                <div class="field-value">{{ value }}</div>
            </div>
            {% endfor %}
            <div class="field">
                <div class="field-label">Status:</div>
                <div class="field-value">
                    {% if client_data.status == 'completed' %}
                        <span style="color: #28a745;">✅ Completo</span>
                    {% else %}
                        <span style="color: #ffc107;">⏳ Coletando</span>
                    {% endif %}
                </div>
            </div>
            {% else %}
            <p>Nenhum dado coletado ainda.</p>
            {% endif %}
            
            <div style="margin-top: 20px; padding-top: 20px; border-top: 1px solid #eee;">
                <h4>🎯 Ações Rápidas</h4>
                <button class="btn" onclick="sendQuickMessage('Ola! Sou um especialista da Equinos Seguros. Como posso ajuda-lo?')">👋 Saudação</button>
                <button class="btn" onclick="sendQuickMessage('Preciso de mais algumas informacoes para finalizar sua cotacao.')">📋 Solicitar Dados</button>
                <button class="btn" onclick="sendQuickMessage('Sua cotacao esta sendo processada. Retorno em breve!')">⏳ Processando</button>
            </div>
        </div>
    </div>

    <script>
        const phone = '{{ phone }}';
        
        document.getElementById('messageForm').addEventListener('submit', function(e) {
            e.preventDefault();
            
            const formData = new FormData();
            formData.append('phone', phone);
            formData.append('message', this.message.value);
            
            fetch('/agent/send-message', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    showAlert('Mensagem enviada com sucesso!', 'success');
                    this.message.value = '';
                    setTimeout(() => location.reload(), 1000);
                } else {
                    showAlert('Erro ao enviar mensagem: ' + data.message, 'danger');
                }
            })
            .catch(error => {
                showAlert('Erro de conexão: ' + error, 'danger');
            });
        });
        
        function sendQuickMessage(message) {
            const formData = new FormData();
            formData.append('phone', phone);
            formData.append('message', message);
            
            fetch('/agent/send-message', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    showAlert('Mensagem rápida enviada!', 'success');
                    setTimeout(() => location.reload(), 1000);
                } else {
                    showAlert('Erro: ' + data.message, 'danger');
                }
            });
        }
        
        function completeQuotation() {
            const pdfUrl = prompt('URL do PDF da cotação (opcional):');
            
            const formData = new FormData();
            formData.append('phone', phone);
            if (pdfUrl) formData.append('pdf_url', pdfUrl);
            
            fetch('/agent/complete-quotation', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    showAlert('Cotação finalizada com sucesso!', 'success');
                    setTimeout(() => location.reload(), 1000);
                } else {
                    showAlert('Erro: ' + data.message, 'danger');
                }
            });
        }
        
        function showAlert(message, type) {
            const alertsDiv = document.getElementById('alerts');
            alertsDiv.innerHTML = `<div class="alert alert-${type}">${message}</div>`;
            setTimeout(() => alertsDiv.innerHTML = '', 5000);
        }
        
        // Auto-scroll para última mensagem
        const messagesDiv = document.getElementById('messages');
        messagesDiv.scrollTop = messagesDiv.scrollHeight;
    </script>
</body>
</html>
"""

QUOTATIONS_LIST_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Cotações - {{ agent_name }}</title>
    <meta charset="utf-8">
    <style>
        body { font-family: Arial, sans-serif; margin: 0; background: #f5f5f5; }
        .header { background: #17a2b8; color: white; padding: 15px 20px; display: flex; justify-content: space-between; align-items: center; }
        .container { padding: 20px; }
        .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-bottom: 30px; }
        .stat-card { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); text-align: center; }
        .quotation-card { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin-bottom: 15px; }
        .quotation-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; }
        .quotation-phone { font-size: 18px; font-weight: bold; color: #17a2b8; }
        .quotation-details { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
        .btn { padding: 8px 16px; background: #007bff; color: white; text-decoration: none; border-radius: 4px; }
        .btn-back { background: #6c757d; }
        .badge { padding: 4px 12px; border-radius: 20px; font-size: 12px; color: white; }
        .badge-success { background: #28a745; }
        .badge-warning { background: #ffc107; color: #000; }
        .badge-danger { background: #dc3545; }
        .badge-info { background: #17a2b8; }
        .badge-bot { background: #28a745; }
        .badge-human { background: #6f42c1; }
    </style>
</head>
<body>
    <div class="header">
        <h1>📋 Cotações Finalizadas</h1>
        <div>
            <a href="/agent/dashboard" class="btn btn-back">⬅ Dashboard</a>
            <a href="/agent/conversations" class="btn">💬 Conversas</a>
            <a href="/agent/logout" class="btn">🚪 Sair</a>
        </div>
    </div>
    
    <div class="container">
        <div class="stats">
            <div class="stat-card">
                <div style="font-size: 32px; font-weight: bold; color: #17a2b8;">{{ quotations|length }}</div>
                <div style="color: #666; margin-top: 5px;">Total de Cotações</div>
            </div>
            <div class="stat-card">
                <div style="font-size: 32px; font-weight: bold; color: #28a745;">
                    {{ quotations|selectattr('completed_by', 'equalto', 'bot')|list|length }}
                </div>
                <div style="color: #666; margin-top: 5px;">🤖 Finalizadas pelo Bot</div>
            </div>
            <div class="stat-card">
                <div style="font-size: 32px; font-weight: bold; color: #6f42c1;">
                    {{ quotations|selectattr('completed_by', 'equalto', 'human')|list|length }}
                </div>
                <div style="color: #666; margin-top: 5px;">👨‍💼 Finalizadas por Humano</div>
            </div>
            <div class="stat-card">
                <div style="font-size: 32px; font-weight: bold; color: #dc3545;">
                    {{ quotations|selectattr('status', 'equalto', 'failed')|list|length }}
                </div>
                <div style="color: #666; margin-top: 5px;">❌ Com Erro</div>
            </div>
        </div>
        
        {% for quot in quotations %}
        <div class="quotation-card">
            <div class="quotation-header">
                <div class="quotation-phone">📱 {{ quot.phone }}</div>
                <div>
                    {% if quot.status == 'completed' %}
                        <span class="badge badge-success">✅ FINALIZADA</span>
                    {% elif quot.status == 'failed' %}
                        <span class="badge badge-danger">❌ ERRO</span>
                    {% else %}
                        <span class="badge badge-info">⏳ PROCESSANDO</span>
                    {% endif %}
                    
                    {% if quot.completed_by == 'bot' %}
                        <span class="badge badge-bot">🤖 BOT</span>
                    {% else %}
                        <span class="badge badge-human">👨‍💼 HUMANO</span>
                    {% endif %}
                </div>
            </div>
            
            <div class="quotation-details">
                <div>
                    <h4>🐴 Dados do Animal</h4>
                    <div><strong>Nome:</strong> {{ quot.client_data.get('nome_animal', 'N/A') }}</div>
                    <div><strong>Raça:</strong> {{ quot.client_data.get('raca', 'N/A') }}</div>
                    <div><strong>Valor:</strong> R$ {{ quot.client_data.get('valor_animal', 'N/A') }}</div>
                    <div><strong>Sexo:</strong> {{ quot.client_data.get('sexo', 'N/A') }}</div>
                </div>
                <div>
                    <h4>📋 Informações da Cotação</h4>
                    <div><strong>Criada em:</strong> {{ quot.created_at.strftime('%d/%m/%Y %H:%M') }}</div>
                    {% if quot.completed_at %}
                    <div><strong>Finalizada em:</strong> {{ quot.completed_at.strftime('%d/%m/%Y %H:%M') }}</div>
                    {% endif %}
                    {% if quot.agent_email %}
                    <div><strong>Agente:</strong> {{ quot.agent_email }}</div>
                    {% endif %}
                    {% if quot.pdf_url %}
                    <div><strong>PDF:</strong> <a href="{{ quot.pdf_url }}" target="_blank">📎 Visualizar</a></div>
                    {% endif %}
                </div>
            </div>
        </div>
        {% endfor %}
        
        {% if not quotations %}
        <div style="text-align: center; padding: 40px; color: #666;">
            <h3>📋 Nenhuma cotação encontrada</h3>
            <p>As cotações finalizadas aparecerão aqui.</p>
        </div>
        {% endif %}
    </div>
</body>
</html>
"""

