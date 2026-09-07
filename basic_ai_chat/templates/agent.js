// ===== Agent DOM =====
const txtAgent = document.getElementById('txt-agent');
const btnSendAgent = document.getElementById('btn-send-agent');

// ===== Agent State =====
const agentHistory = [];

// ===== Утилиты =====
function getToolLabel(toolName) {
    const labels = {
        'compare_responses': 'Сравнение вариантов генерации',
        'get_model_info': 'Получение информации о модели',
        'ask_user': 'Уточняющий вопрос',
    };
    return labels[toolName] || toolName;
}

function ordinalDative(n) {
    const suffixes = { 1: '1-му', 2: '2-му', 3: '3-му', 4: '4-му', 5: '5-му' };
    return suffixes[n] || `${n}-му`;
}

function ordinalGenitive(n) {
    const suffixes = { 1: '1-го', 2: '2-го', 3: '3-го', 4: '4-го', 5: '5-го' };
    return suffixes[n] || `${n}-го`;
}

function renderConstraintChips(constraints) {
    const labels = {
        temperature: 'Температура',
        max_tokens: 'Длина',
        stop: 'Стоп-символ',
        response_format: 'Формат',
        reasoning_effort: 'Reasoning',
    };
    const chips = [];
    for (const [key, value] of Object.entries(constraints || {})) {
        if (value === null || value === undefined) continue;
        const name = labels[key] || key;
        const val = typeof value === 'object' ? JSON.stringify(value) : String(value);
        chips.push(`<span class="param-badge">${escapeHtml(name)}: ${escapeHtml(val)}</span>`);
    }
    if (!chips.length) return '';
    return `<div class="params-block">${chips.join('')}</div>`;
}

function renderCompareGraph(toolArgs, toolResult) {
    const results = (toolResult && toolResult.results) || [];
    const message = (toolArgs && toolArgs.message) || '';
    let html = '';

    // Верхняя строка: dispatch (отправка запросов субагентам)
    html += '<div class="ai-responses ai-responses--graph">';
    for (let i = 0; i < results.length; i++) {
        const r = results[i];
        html += '<div class="ai-response-col">';
        html += `<div class="msg-label">Агент обращается к ${ordinalDative(i + 1)} субагенту</div>`;
        html += `<div class="message ai"><div class="bubble">${escapeHtml(message)}</div></div>`;
        html += renderConstraintChips(r.constraints);
        html += renderRawJson('JSON-запрос', r.response?.raw_request);
        html += '</div>';
    }
    html += '</div>';

    // Нижняя строка: ответы субагентов
    html += '<div class="ai-responses ai-responses--graph">';
    for (let i = 0; i < results.length; i++) {
        const r = results[i];
        html += '<div class="ai-response-col">';
        html += `<div class="msg-label">Ответ ${ordinalGenitive(i + 1)} субагента</div>`;
        if (r.error) {
            html += `<div class="message ai"><div class="bubble">Ошибка: ${escapeHtml(r.error)}</div></div>`;
        } else if (r.response) {
            const text = r.response.content;
            if (text) {
                html += `<div class="message ai"><div class="bubble">${text}</div></div>`;
            } else {
                html += `<div class="message ai"><div class="bubble">(пустой ответ)</div></div>`;
            }
            if (r.response.usage) {
                html += renderBadges(null, null, r.response.usage);
            }
            html += renderRawJson('JSON-ответ', r.response.raw);
        }
        html += '</div>';
    }
    html += '</div>';

    return html;
}

// ===== Отправка задачи агенту =====
async function sendAgentTask() {
    const text = txtAgent.value.trim();
    if (!text) return;
    txtAgent.value = '';
    txtAgent.style.height = 'auto';
    btnSendAgent.disabled = true;

    // Блокируем ввод
    txtAgent.disabled = true;
    btnSendAgent.disabled = true;

    try {
        const resp = await fetch('/api/agent', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message: text,
                history: agentHistory,
            }),
        });

        const data = await resp.json();

        if (data.error) {
            const errMsg = `Ошибка: ${escapeHtml(data.error)}`;
            addTurn(text, errMsg, null, null, null, null, null, false);
            return;
        }

        // Обновляем историю
        agentHistory.push({ role: 'user', content: text });
        agentHistory.push({ role: 'assistant', content: data.content });

        // Рендерим ответ
        try {
            renderAgentResponse(text, data);
        } catch (renderErr) {
            console.error('Ошибка рендера ответа агента:', renderErr);
            appendAgentErrorRow(`Ошибка отображения: ${escapeHtml(renderErr.message)}`);
        }

    } catch (err) {
        const errMsg = `Ошибка сети: ${escapeHtml(err.message)}`;
        addTurn(text, errMsg, null, null, null, null, null, false);
    } finally {
        txtAgent.disabled = false;
        btnSendAgent.disabled = !txtAgent.value.trim();
        txtAgent.focus();
    }
}

function appendAgentErrorRow(message) {
    const row = document.createElement('div');
    row.className = 'chat-row row-ai';
    row.innerHTML = `
        <div class="msg-label">Агент</div>
        <div class="message ai"><div class="bubble">${message}</div></div>
    `;
    container.appendChild(row);
    scrollToBottom();
}

// ===== Рендер ответа агента =====
// Первый запрос этого хода: system + история + user(сообщение клиента),
// без внутренних assistant(JSON тула) и user(«Результат инструмента…»)
function renderClientRequest(data) {
    const firstCall = (data.steps || []).find(s => s.type === 'tool_call' && s.raw_request);
    return (firstCall && firstCall.raw_request) || data.raw_request;
}

function renderAgentResponse(userText, data) {
    // 1. Сообщение пользователя
    const userRow = document.createElement('div');
    userRow.className = 'chat-row row-user';
    let userContent = `
        <div class="msg-label">Вы</div>
        <div class="message user"><div class="bubble">${escapeHtml(userText)}</div></div>
    `;
    userContent += renderRawJson('JSON-запрос', renderClientRequest(data));
    userRow.innerHTML = userContent;
    container.appendChild(userRow);
    fitJsonWidthToBubble(userRow);

    // 2. Каждый проход агента — реплика «Агент · Шаг N» с человекочитаемым текстом
    let stepNum = 0;
    const steps = data.steps || [];
    for (let i = 0; i < steps.length; i++) {
        const step = steps[i];
        if (step.type !== 'tool_call') continue;
        stepNum++;
        const next = steps[i + 1];

        if (step.tool_name === 'compare_responses') {
            // Реплика «Сравниваю N вариантов…» + сам граф сравнения
            let inner = buildToolCallExtras(step);
            if (next && next.type === 'tool_result' && next.tool_name === 'compare_responses') {
                inner += renderCompareGraph(step.tool_args || next.tool_args, next.tool_result);
                i++;
            }
            renderAgentMessageRow(stepNum, agentStepText(step), inner);
        } else {
            // Обычный тул: реплика «Вызываю…/Запрашиваю…» + результат инструмента
            let inner = buildToolCallExtras(step);
            if (next && next.type === 'tool_result') {
                if (step.tool_name !== 'ask_user') {
                    inner += toolResultPre(next);
                }
                i++;
            }
            renderAgentMessageRow(stepNum, agentStepText(step), inner);
        }
    }

    // 3. Финальный ответ агента
    stepNum++;
    renderAgentAnswerRow(data, stepNum);

    scrollToBottom();
}

function agentStepText(step) {
    if (step.tool_name === 'compare_responses') {
        const variants = (step.tool_args && step.tool_args.variants) || [];
        const n = variants.length;
        const word = n === 1 ? 'вариант' : (n >= 2 && n <= 4 ? 'варианта' : 'вариантов');
        return `Сравниваю ${n} ${word} генерации`;
    }
    if (step.tool_name === 'get_model_info') return 'Запрашиваю информацию о модели';
    if (step.tool_name === 'ask_user') return 'Задаю уточняющий вопрос';
    return `Вызываю инструмент «${getToolLabel(step.tool_name)}»`;
}

function buildToolCallExtras(step) {
    let html = '';
    if (step.raw_request) {
        html += renderBadges(null, null, step.usage);
        html += renderRawJson('JSON-ответ', step.raw_response);
    }
    return html;
}

function toolResultPre(step) {
    if (!step.tool_result) return '';
    const resultStr = JSON.stringify(step.tool_result, null, 2);
    return `<pre class="tool-result"><code>${escapeHtml(resultStr)}</code></pre>`;
}

function renderAgentMessageRow(stepNum, bubbleText, innerHtml) {
    const row = document.createElement('div');
    row.className = 'chat-row row-ai';
    let html = `<div class="msg-label">Агент · Шаг ${stepNum}</div>`;
    html += '<div class="ai-responses ai-responses--single"><div class="ai-response-col">';
    html += `<div class="message ai"><div class="bubble">${escapeHtml(bubbleText)}</div></div>`;
    html += innerHtml;
    html += '</div></div>';
    row.innerHTML = html;
    container.appendChild(row);
}

function renderAgentAnswerRow(data, stepNum) {
    const row = document.createElement('div');
    row.className = 'chat-row row-ai';
    let html = `<div class="msg-label">Агент · Шаг ${stepNum}</div>`;
    html += '<div class="ai-responses ai-responses--single"><div class="ai-response-col">';
    html += `<div class="message ai"><div class="bubble">${data.content}</div></div>`;
    html += renderBadges(null, null, data.usage);
    html += renderRawJson('JSON-ответ', data.raw_response);
    html += '</div></div>';
    row.innerHTML = html;
    container.appendChild(row);
}

// ===== Инициализация =====
txtAgent.addEventListener('input', () => {
    btnSendAgent.disabled = !txtAgent.value.trim();
    txtAgent.style.height = 'auto';
    txtAgent.style.height = txtAgent.scrollHeight + 'px';
});

txtAgent.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendAgentTask();
    }
});

btnSendAgent.addEventListener('click', sendAgentTask);
